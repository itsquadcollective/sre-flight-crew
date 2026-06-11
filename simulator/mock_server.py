# simulator/mock_server.py
#
# PURPOSE: This is the fake server that crashes during the demo.
# It runs as a real HTTP server. The Watchman reads its log file.
# The Fixer calls GET /health to confirm recovery.
#
# HOW TO RUN:
#   python simulator/mock_server.py
#
# HOW TO TRIGGER FAILURES (open browser or second terminal):
#   http://localhost:8080/inject/db_crash      <- USE THIS FOR DEMO
#   http://localhost:8080/inject/http500
#   http://localhost:8080/inject/http504
#   http://localhost:8080/inject/memory_spike
#   http://localhost:8080/inject/recover       <- RESETS TO HEALTHY

import uvicorn
import logging
import threading
import time
import os
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ─── LOG SETUP ───────────────────────────────────────────────────────────────
# Writes logs to terminal AND to simulator/server.log
# The Watchman reads simulator/server.log to detect failures

LOG_FILE = "simulator/server.log"
os.makedirs("simulator", exist_ok=True)

logger = logging.getLogger("mock_server")
logger.setLevel(logging.DEBUG)

terminal_handler = logging.StreamHandler()
terminal_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

log_format = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
terminal_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)
logger.addHandler(terminal_handler)
logger.addHandler(file_handler)


# ─── SERVER STATE ─────────────────────────────────────────────────────────────
# Holds the current health of the simulated server

server_state = {
    "status": "healthy",
    "failure_type": None,
    "failure_active": False,
    "crash_timestamp": None,
    "request_count": 0,
    "db_connected": True,
    "memory_usage_percent": 42.0,
}

state_lock = threading.Lock()
app = FastAPI(title="SRE Flight Crew Mock Server")


# ─── NORMAL ENDPOINTS ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    with state_lock:
        if server_state["failure_active"]:
            return _failure_response()
        server_state["request_count"] += 1
    logger.info(f"web_server: GET / — 200 OK (request #{server_state['request_count']})")
    return JSONResponse(status_code=200, content={"status": "ok", "page": "homepage"})


@app.get("/checkout")
async def checkout():
    with state_lock:
        if server_state["failure_active"]:
            return _failure_response()
        if not server_state["db_connected"]:
            logger.error("checkout_api: database unavailable — cannot process order")
            logger.error("checkout_api: OperationalError: could not connect to server: Connection refused")
            return JSONResponse(status_code=500, content={"error": "Database unavailable"})
        server_state["request_count"] += 1
    logger.info("checkout_api: GET /checkout — 200 OK")
    return JSONResponse(status_code=200, content={"status": "ok", "page": "checkout"})


@app.get("/health")
async def health_check():
    """
    The Fixer calls this after running a recovery script.
    Returns 200 only when fully healthy — this flips dashboard to GREEN.
    """
    with state_lock:
        if server_state["failure_active"] or not server_state["db_connected"]:
            logger.warning("health_check: GET /health — 503 Service Unavailable")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "failure_type": server_state["failure_type"],
                    "db_connected": server_state["db_connected"],
                    "memory_usage_percent": server_state["memory_usage_percent"]
                }
            )
    logger.info("health_check: GET /health — 200 OK — all systems nominal")
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "db_connected": server_state["db_connected"],
            "memory_usage_percent": server_state["memory_usage_percent"],
            "uptime_requests": server_state["request_count"]
        }
    )


# ─── FAILURE INJECTION ENDPOINTS ──────────────────────────────────────────────

@app.get("/inject/db_crash")
async def inject_db_crash():
    """
    PRIMARY DEMO SCENARIO.
    Simulates PostgreSQL running out of memory and crashing.
    Watchman detects this. Diagnoser maps it to runbook_db_crash.md.
    """
    with state_lock:
        server_state["status"] = "crashed"
        server_state["failure_active"] = True
        server_state["failure_type"] = "DB_CRASH"
        server_state["db_connected"] = False
        server_state["crash_timestamp"] = datetime.now(timezone.utc).isoformat()

    logger.info("db_container: PostgreSQL 15.2 running normally")
    logger.warning("db_container: memory usage approaching limit — 89%")
    logger.warning("db_container: memory usage critical — 97%")
    logger.error("db_container: out of memory — killing process")
    logger.error("db_container: PostgreSQL process terminated unexpectedly")
    logger.error("db_container: OperationalError: could not connect to server: Connection refused")
    logger.error("db_container: Is the server running on host 'localhost' accepting TCP/IP on port 5432?")
    logger.error("checkout_api: database connection pool exhausted — all connections refused")
    logger.error("checkout_api: OperationalError: could not connect to server: Connection refused (PostgreSQL port 5432)")
    logger.error("web_server: HTTP 500 Internal Server Error — database unavailable")

    print("\n🔴 FAILURE INJECTED: DB_CRASH — Watchman should detect this now\n")
    return JSONResponse(status_code=200, content={"injected": "DB_CRASH"})


@app.get("/inject/http500")
async def inject_http500():
    with state_lock:
        server_state["status"] = "degraded"
        server_state["failure_active"] = True
        server_state["failure_type"] = "HTTP_500"
        server_state["crash_timestamp"] = datetime.now(timezone.utc).isoformat()

    logger.error("web_server: Unhandled exception in request handler")
    logger.error("web_server: RuntimeError: internal processing failed")
    logger.error("checkout_api: upstream dependency failure — aborting request")
    logger.error("web_server: HTTP 500 Internal Server Error")

    print("\n🔴 FAILURE INJECTED: HTTP 500\n")
    return JSONResponse(status_code=200, content={"injected": "HTTP_500"})


@app.get("/inject/http504")
async def inject_http504():
    with state_lock:
        server_state["status"] = "degraded"
        server_state["failure_active"] = True
        server_state["failure_type"] = "HTTP_504"
        server_state["crash_timestamp"] = datetime.now(timezone.utc).isoformat()

    logger.warning("gateway: upstream service not responding — retrying (1/3)")
    logger.warning("gateway: upstream service not responding — retrying (2/3)")
    logger.warning("gateway: upstream service not responding — retrying (3/3)")
    logger.error("gateway: all retries exhausted — upstream unreachable")
    logger.error("gateway: HTTP 504 Gateway Timeout")
    logger.error("web_server: HTTP 504 Gateway Timeout — upstream did not respond in time")

    print("\n🔴 FAILURE INJECTED: HTTP 504\n")
    return JSONResponse(status_code=200, content={"injected": "HTTP_504"})


@app.get("/inject/memory_spike")
async def inject_memory_spike():
    with state_lock:
        server_state["status"] = "degraded"
        server_state["failure_active"] = True
        server_state["failure_type"] = "MEMORY_SPIKE"
        server_state["memory_usage_percent"] = 97.3
        server_state["crash_timestamp"] = datetime.now(timezone.utc).isoformat()

    logger.warning("system_monitor: memory usage spike detected — 87.2%")
    logger.warning("system_monitor: memory usage rising — 91.8%")
    logger.error("system_monitor: memory usage ALERT — 97.3% — above critical threshold")
    logger.error("system_monitor: OOM killer may activate — immediate action required")
    logger.error("system_monitor: MEMORY_SPIKE — 97.3% utilization on web_server")

    print("\n🔴 FAILURE INJECTED: MEMORY_SPIKE\n")
    return JSONResponse(status_code=200, content={"injected": "MEMORY_SPIKE"})


@app.get("/inject/recover")
async def inject_recover():
    """
    Resets server back to healthy.
    Call this to reset between demo runs.
    """
    with state_lock:
        server_state["status"] = "healthy"
        server_state["failure_active"] = False
        server_state["failure_type"] = None
        server_state["db_connected"] = True
        server_state["memory_usage_percent"] = 42.0
        server_state["crash_timestamp"] = None

    logger.info("recovery: database connection re-established — port 5432 responding")
    logger.info("recovery: memory usage normalised — 42.0%")
    logger.info("recovery: all systems nominal — server healthy")
    logger.info("web_server: accepting requests normally")

    print("\n🟢 SERVER RECOVERED — all systems healthy\n")
    return JSONResponse(status_code=200, content={"status": "recovered"})


@app.get("/status")
async def get_status():
    with state_lock:
        return JSONResponse(status_code=200, content=server_state)


# ─── BACKGROUND TRAFFIC SIMULATOR ─────────────────────────────────────────────
# Writes realistic normal log entries every 3 seconds
# Makes the log look like a live server — important for demo realism

def simulate_normal_traffic():
    endpoints = ["/", "/checkout", "/products", "/cart", "/api/inventory"]
    response_times = [12, 23, 8, 45, 19, 31, 14, 27]
    i = 0
    while True:
        time.sleep(3)
        with state_lock:
            is_failing = server_state["failure_active"]
        if not is_failing:
            endpoint = endpoints[i % len(endpoints)]
            ms = response_times[i % len(response_times)]
            logger.info(f"web_server: GET {endpoint} — 200 OK — {ms}ms")
            i += 1


# ─── STARTUP ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("web_server: SRE Flight Crew Mock Server starting up")
    logger.info("web_server: PostgreSQL connection established — port 5432")
    logger.info("web_server: cache service connected — port 6379")
    logger.info("web_server: all systems nominal — accepting requests on port 8080")

    traffic_thread = threading.Thread(target=simulate_normal_traffic, daemon=True)
    traffic_thread.start()
    logger.info("web_server: background traffic simulator started")


if __name__ == "__main__":
    print("=" * 55)
    print("  SRE Flight Crew — Mock Server")
    print("  Running on: http://localhost:8080")
    print("  Log file:   simulator/server.log")
    print("=" * 55)
    print()
    print("  Inject failures:")
    print("  http://localhost:8080/inject/db_crash      <- PRIMARY DEMO")
    print("  http://localhost:8080/inject/http500")
    print("  http://localhost:8080/inject/http504")
    print("  http://localhost:8080/inject/memory_spike")
    print("  http://localhost:8080/inject/recover       <- RESET")
    print()
    uvicorn.run("simulator.mock_server:app", host="0.0.0.0", port=8080, reload=False)