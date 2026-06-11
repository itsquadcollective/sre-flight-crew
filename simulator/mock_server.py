"""The "Target" — a simulated production web server that the agents protect.

Run:    uvicorn simulator.mock_server:app --port 8090
        (8080 is often blocked on Windows — port comes from .env via shared/config.py)
Or:     python -m simulator.mock_server

Public endpoints (the "production site"):
    GET  /            landing page
    GET  /health      200 {"status": "ok"} when healthy, 500 when crashed
    GET  /api/orders  sample business endpoint, 500s when crashed

Simulation control API (used by failure_injector + Fixer recovery scripts):
    POST /sim/inject/{failure}   failure: db_crash | memory_spike
    POST /sim/recover/{action}   action:  restart_db | clear_cache
    GET  /sim/state              current internal state (for dashboard/tests)

Every request and failure writes structured lines to logs/server.log —
that file is the Watchman's input.
"""
import logging
import threading
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from shared.config import MOCK_SERVER_HOST, MOCK_SERVER_PORT, SERVER_LOG_PATH

# ─── Failure catalogue ────────────────────────────────────────────────────────
# error_type values match shared/schemas.py ErrorEvent.error_type
FAILURES = {
    "db_crash": {
        "error_type": "DB_CRASH",
        "message": "FATAL: database connection pool exhausted — lock not released on table 'orders'",
        "detail_logs": [
            "ERROR [db-pool] connection 14/15/16 timed out after 30000ms",
            "ERROR [db-pool] deadlock detected: transaction 0x7f3a holds lock on 'orders'",
            "FATAL [api] DB_CRASH: all upstream queries failing, returning HTTP 500",
        ],
        "recovery_action": "restart_db",
    },
    "memory_spike": {
        "error_type": "MEMORY_SPIKE",
        "message": "CRITICAL: heap usage 97% — response cache grew unbounded, GC thrashing",
        "detail_logs": [
            "WARN  [cache] response cache at 1.9M entries (no eviction policy hit)",
            "ERROR [runtime] MEMORY_SPIKE: heap 97%, allocation failures in request handlers",
            "FATAL [api] worker unresponsive >10s, returning HTTP 500",
        ],
        "recovery_action": "clear_cache",
    },
}

VALID_RECOVERY = {f["recovery_action"]: name for name, f in FAILURES.items()}


# ─── Server state (thread-safe) ───────────────────────────────────────────────
class ServerState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.healthy = True
        self.active_failure: str | None = None  # key into FAILURES
        self.crash_count = 0
        self.recovery_count = 0

    def crash(self, failure: str) -> None:
        with self._lock:
            self.healthy = False
            self.active_failure = failure
            self.crash_count += 1

    def recover(self) -> None:
        with self._lock:
            self.healthy = True
            self.active_failure = None
            self.recovery_count += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "healthy": self.healthy,
                "active_failure": self.active_failure,
                "error_type": FAILURES[self.active_failure]["error_type"] if self.active_failure else None,
                "crash_count": self.crash_count,
                "recovery_count": self.recovery_count,
            }


state = ServerState()

# ─── Structured logging to logs/server.log (the Watchman's input) ─────────────
SERVER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("mock_server")
log.setLevel(logging.INFO)
_handler = logging.FileHandler(SERVER_LOG_PATH)
_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"))
log.addHandler(_handler)
log.addHandler(logging.StreamHandler())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="QuadShop — simulated production server")


def _crashed_response() -> JSONResponse:
    failure = FAILURES[state.active_failure]
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": failure["error_type"],
            "message": failure["message"],
            "timestamp": _now(),
        },
    )


@app.get("/")
def index():
    if not state.healthy:
        log.info("ERROR [api] GET / -> 500 (%s)", FAILURES[state.active_failure]["error_type"])
        return _crashed_response()
    log.info("INFO  [api] GET / -> 200")
    return {"app": "QuadShop", "status": "ok", "message": "Welcome to the simulated production site"}


@app.get("/health")
def health():
    if not state.healthy:
        log.info("ERROR [health] GET /health -> 500 (%s)", FAILURES[state.active_failure]["error_type"])
        return _crashed_response()
    log.info("INFO  [health] GET /health -> 200")
    return {"status": "ok", "timestamp": _now()}


@app.get("/api/orders")
def orders():
    if not state.healthy:
        log.info("ERROR [api] GET /api/orders -> 500 (%s)", FAILURES[state.active_failure]["error_type"])
        return _crashed_response()
    log.info("INFO  [api] GET /api/orders -> 200 (3 orders)")
    return {"orders": [{"id": 1, "item": "rubber duck"}, {"id": 2, "item": "keyboard"}, {"id": 3, "item": "gpu"}]}


# ─── Simulation control API ───────────────────────────────────────────────────
@app.post("/sim/inject/{failure}")
def inject(failure: str, response: Response):
    if failure not in FAILURES:
        response.status_code = 400
        return {"error": f"unknown failure '{failure}'", "valid": list(FAILURES)}
    state.crash(failure)
    spec = FAILURES[failure]
    for line in spec["detail_logs"]:
        log.info("%s", line)
    log.info("FATAL [system] %s — service DOWN", spec["error_type"])
    return {"injected": failure, "error_type": spec["error_type"], "state": state.snapshot()}


@app.post("/sim/recover/{action}")
def recover(action: str, response: Response):
    if action not in VALID_RECOVERY:
        response.status_code = 400
        return {"error": f"unknown action '{action}'", "valid": list(VALID_RECOVERY)}
    snap = state.snapshot()
    if snap["healthy"]:
        return {"recovered": False, "detail": "server already healthy", "state": snap}
    expected = FAILURES[snap["active_failure"]]["recovery_action"]
    if action != expected:
        log.info("ERROR [recovery] action '%s' had no effect on %s", action, snap["error_type"])
        response.status_code = 409
        return {"recovered": False, "detail": f"'{action}' does not fix {snap['error_type']} (needs '{expected}')",
                "state": state.snapshot()}
    log.info("INFO  [recovery] executing '%s' ...", action)
    state.recover()
    log.info("INFO  [recovery] '%s' succeeded — service RESTORED", action)
    return {"recovered": True, "action": action, "state": state.snapshot()}


@app.get("/sim/state")
def sim_state():
    return state.snapshot()


if __name__ == "__main__":
    uvicorn.run(app, host=MOCK_SERVER_HOST, port=MOCK_SERVER_PORT)
