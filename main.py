<<<<<<< HEAD
"""SRE Flight Crew — orchestrator. Wires Watchman → Diagnoser → Fixer.

Run:
    python main.py            # watch mode: polls /health, reacts to real crashes
    python main.py --demo     # demo mode: auto-injects a crash after 5s, full loop
    python main.py --demo --failure memory_spike

Prereq: the target server must be running:
    uvicorn simulator.mock_server:app --port 8090

AGENT DEVS — your integration points (replace the Stub* classes):
    agents/diagnoser/diagnoser_agent.py  ->  class DiagnoserAgent:
        def diagnose(self, event: ErrorEvent) -> DiagnosisResult
    agents/fixer/fixer_agent.py          ->  class FixerAgent:
        def fix(self, diagnosis: DiagnosisResult) -> FixResult
The orchestrator auto-detects your classes; until they exist it falls back to
rule-based stubs so the demo loop always runs end-to-end.
"""
import argparse
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

from shared.config import (
    HEALTH_CHECK_INTERVAL_SECONDS,
    HEALTH_CHECK_URL,
    MOCK_SERVER_URL,
    PROJECT_ROOT,
)
from shared.event_bus import (
    bus,
    TOPIC_ERROR_DETECTED,
    TOPIC_ERROR_DIAGNOSED,
    TOPIC_ERROR_FIXED,
)
from shared.schemas import DiagnosisResult, ErrorEvent, FixResult, SystemStatus

STATUS_PATH = PROJECT_ROOT / "logs" / "status.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Stub agents (used until the real ones land) ─────────────────────────────
class StubDiagnoser:
    """Rule-based fallback. Real one uses Foundry IQ + knowledge base."""

    RULES = {
        "DB_CRASH": ("restart_db", "agents/fixer/recovery_scripts/restart_db.sh",
                     "runbook_db_crash.md", "Database connection pool deadlocked; locks not released."),
        "MEMORY_SPIKE": ("clear_cache", "agents/fixer/recovery_scripts/clear_cache.sh",
                         "runbook_memory_spike.md", "Unbounded response cache exhausted heap memory."),
    }

    def diagnose(self, event: ErrorEvent) -> DiagnosisResult:
        action, script, runbook, cause = self.RULES.get(
            event.error_type,
            ("restart_service", "", "sop_general.md", "Unknown failure; generic restart recommended."),
        )
        return DiagnosisResult(
            event_id=event.event_id,
            root_cause=cause,
            confidence=0.95,
            recovery_action=action,
            script_path=script,
            safety_confirmed=True,
            runbook_reference=runbook,
            reasoning_summary=f"[STUB] matched error_type={event.error_type} against static rules",
        )


class StubFixer:
    """Runs the recovery script; falls back to the sim HTTP API when bash is unavailable (Windows)."""

    def fix(self, diagnosis: DiagnosisResult) -> FixResult:
        start = time.monotonic()
        ok, detail = self._execute(diagnosis)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        try:
            health = requests.get(HEALTH_CHECK_URL, timeout=5).status_code
        except requests.RequestException:
            health = 0
        return FixResult(
            event_id=diagnosis.event_id,
            action_taken=diagnosis.recovery_action,
            success=ok and health == 200,
            health_check_status=health,
            resolution_time_ms=elapsed_ms,
            timestamp_resolved=_now_iso(),
            error_message="" if ok else detail,
        )

    def _execute(self, diagnosis: DiagnosisResult) -> tuple[bool, str]:
        script = PROJECT_ROOT / diagnosis.script_path if diagnosis.script_path else None
        if script and script.exists() and shutil.which("bash"):
            r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=60)
            return r.returncode == 0, r.stderr[-500:]
        # No bash (plain Windows) — call the sim recovery endpoint directly
        try:
            r = requests.post(f"{MOCK_SERVER_URL}/sim/recover/{diagnosis.recovery_action}", timeout=10)
            return r.status_code == 200, r.text[:500]
        except requests.RequestException as e:
            return False, str(e)


# ─── Orchestrator ─────────────────────────────────────────────────────────────
class Orchestrator:
    def __init__(self) -> None:
        self.diagnoser = self._load("agents.diagnoser.diagnoser_agent", "DiagnoserAgent", StubDiagnoser)
        self.fixer = self._load("agents.fixer.fixer_agent", "FixerAgent", StubFixer)
        self._active_incident = False
        self._current_event_id = ""
        self._resolved_count = 0
        self._last_resolution_ms = 0
        self._stop = threading.Event()
        bus.subscribe(TOPIC_ERROR_DETECTED, self._on_detected)
        bus.subscribe(TOPIC_ERROR_DIAGNOSED, self._on_diagnosed)
        bus.subscribe(TOPIC_ERROR_FIXED, self._on_fixed)

    @staticmethod
    def _load(module: str, cls: str, fallback: type):
        try:
            mod = __import__(module, fromlist=[cls])
            agent = getattr(mod, cls)()
            print(f"[orchestrator] using real {cls}")
            return agent
        except (ImportError, AttributeError):
            print(f"[orchestrator] {cls} not implemented yet — using {fallback.__name__}")
            return fallback()

    # ── pipeline handlers ──
    def _on_detected(self, event: ErrorEvent) -> None:
        print(f"🔍 [watchman]  detected {event.error_type} ({event.event_id})")
        self._write_status("incident")
        diagnosis = self.diagnoser.diagnose(event)
        bus.publish(TOPIC_ERROR_DIAGNOSED, diagnosis)

    def _on_diagnosed(self, diagnosis: DiagnosisResult) -> None:
        print(f"🧠 [diagnoser] {diagnosis.root_cause}")
        print(f"             → action: {diagnosis.recovery_action} (confidence {diagnosis.confidence:.0%})")
        self._write_status("recovering")
        result = self.fixer.fix(diagnosis)
        bus.publish(TOPIC_ERROR_FIXED, result)

    def _on_fixed(self, result: FixResult) -> None:
        if result.success:
            self._resolved_count += 1
            self._last_resolution_ms = result.resolution_time_ms
            print(f"🔧 [fixer]     ✓ {result.action_taken} succeeded in {result.resolution_time_ms}ms — service RESTORED")
        else:
            print(f"🔧 [fixer]     ✗ {result.action_taken} FAILED: {result.error_message}")
        self._active_incident = False
        self._write_status("healthy" if result.success else "degraded")

    # ── watch loop ──
    def watch(self) -> None:
        print(f"[orchestrator] watching {HEALTH_CHECK_URL} every {HEALTH_CHECK_INTERVAL_SECONDS}s (Ctrl+C to stop)")
        self._write_status("healthy")
        while not self._stop.is_set():
            try:
                code = requests.get(HEALTH_CHECK_URL, timeout=5).status_code
            except requests.RequestException:
                code = 0
            if code != 200 and not self._active_incident:
                self._active_incident = True
                event = self._build_event(code)
                bus.publish(TOPIC_ERROR_DETECTED, event)
            elif code == 200 and not self._active_incident:
                self._write_status("healthy")
            self._stop.wait(HEALTH_CHECK_INTERVAL_SECONDS)

    def _build_event(self, http_code: int) -> ErrorEvent:
        """Builds the ErrorEvent from live server state + recent log lines.
        AGENT DEVS (Watchman): replace this with real log parsing in
        agents/watchman/log_parser.py — interface stays the same."""
        try:
            sim = requests.get(f"{MOCK_SERVER_URL}/sim/state", timeout=5).json()
            error_type = sim.get("error_type") or "HTTP_500"
        except requests.RequestException:
            error_type = "HTTP_500"
        log_path = PROJECT_ROOT / "logs" / "server.log"
        snippet = ""
        if log_path.exists():
            snippet = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-10:])
        self._current_event_id = f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        return ErrorEvent(
            event_id=self._current_event_id,
            timestamp=_now_iso(),
            error_type=error_type,
            error_message=f"health check returned HTTP {http_code or 'timeout'}",
            affected_service="mock_server",
            severity="critical",
            raw_log_snippet=snippet,
        )

    def _write_status(self, status: str) -> None:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(SystemStatus(
            status=status,
            last_updated=_now_iso(),
            active_incident=self._active_incident,
            current_event_id=self._current_event_id,
            last_resolution_ms=self._last_resolution_ms,
            total_incidents_resolved=self._resolved_count,
        ).to_json(), encoding="utf-8")

    def stop(self) -> None:
        self._stop.set()


def _demo_injector(failure: str, delay: float = 5.0) -> None:
    time.sleep(delay)
    print(f"\n💥 [demo] injecting '{failure}' ...")
    requests.post(f"{MOCK_SERVER_URL}/sim/inject/{failure}", timeout=5)


def main() -> None:
    p = argparse.ArgumentParser(description="SRE Flight Crew orchestrator")
    p.add_argument("--demo", action="store_true", help="auto-inject a crash 5s after start")
    p.add_argument("--failure", default="db_crash", choices=["db_crash", "memory_spike"])
    args = p.parse_args()

    try:
        requests.get(HEALTH_CHECK_URL, timeout=3)
    except requests.RequestException:
        print(f"✗ target server not reachable at {HEALTH_CHECK_URL} — start it first:")
        print("    uvicorn simulator.mock_server:app --port 8090")
        raise SystemExit(1)

    orch = Orchestrator()
    if args.demo:
        threading.Thread(target=_demo_injector, args=(args.failure,), daemon=True).start()
    try:
        orch.watch()
    except KeyboardInterrupt:
        orch.stop()
        print("\n[orchestrator] stopped")
=======
# main.py
# ─────────────────────────────────────────────────────────────────────────────
# SRE Flight Crew — Pipeline Orchestrator
#
# Runs the full autonomous incident-response pipeline:
#   1. Watchman monitors logs/server.log for errors
#   2. Diagnoser analyzes the error via Azure AI Foundry Agent Service
#   3. Fixer executes the prescribed recovery action
#   4. Chronicler logs the incident to data/pattern_memory.json
#
# Usage:
#   python main.py
#
# The pipeline runs continuously until Ctrl+C.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from shared.config import (
    SERVER_LOG_PATH,
    MOCK_SERVER_URL,
    HEALTH_CHECK_URL,
    PATTERN_MEMORY_PATH,
)
from shared.schemas import ErrorEvent, DiagnosisResult, FixResult
from shared.event_bus import bus, TOPIC_ERROR_DETECTED, TOPIC_ERROR_DIAGNOSED, TOPIC_ERROR_FIXED

from agents.watchman.watchman_agent import WatchmanAgent
from agents.diagnoser.diagnoser_agent import Diagnoser
from agents.fixer.fixer_agent import FixerAgent


# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sre.pipeline")


# ─── Chronicler (inline — Agent 4) ──────────────────────────────────────────
# The Chronicler is simple enough to be inline: it appends resolved incidents
# to data/pattern_memory.json. If it grows complex, extract to its own module.

def record_incident(
    event: ErrorEvent,
    diagnosis: DiagnosisResult,
    fix: FixResult,
) -> None:
    """
    Append a resolved incident to pattern_memory.json.

    This is the Chronicler's job — building institutional memory so the
    Diagnoser can detect recurring patterns in future incidents.
    """
    memory_path = Path(PATTERN_MEMORY_PATH)
    memory_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing data
    if memory_path.exists():
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"incidents": [], "total_resolved": 0, "last_updated": ""}

    # Append new incident
    incident_record = {
        "event_id": event.event_id,
        "timestamp": event.timestamp,
        "error_type": event.error_type,
        "root_cause": diagnosis.root_cause,
        "recovery_action": diagnosis.recovery_action,
        "confidence": diagnosis.confidence,
        "resolution_time_ms": fix.resolution_time_ms,
        "success": fix.success,
        "reasoning_summary": diagnosis.reasoning_summary[:500],
    }

    data["incidents"].append(incident_record)
    data["total_resolved"] = len([i for i in data["incidents"] if i["success"]])
    data["last_updated"] = datetime.now(timezone.utc).isoformat()

    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(
        "[CHRONICLER] Incident %s recorded | total_resolved=%d",
        event.event_id,
        data["total_resolved"],
    )


# ─── Pipeline ────────────────────────────────────────────────────────────────

async def run_pipeline() -> None:
    """
    Main pipeline loop. Initializes all agents, then loops:
    detect → diagnose → fix → record.
    """
    print()
    print("=" * 60)
    print("  SRE FLIGHT CREW — Autonomous Incident Response Pipeline")
    print("=" * 60)
    print()
    print(f"  Mock server URL:  {MOCK_SERVER_URL}")
    print(f"  Health check URL: {HEALTH_CHECK_URL}")
    print(f"  Log file:         {SERVER_LOG_PATH}")
    print(f"  Pattern memory:   {PATTERN_MEMORY_PATH}")
    print()

    # ── Initialize agents ────────────────────────────────────────────────
    logger.info("[PIPELINE] Initializing agents...")

    watchman = WatchmanAgent()
    logger.info("[PIPELINE] ✓ Watchman ready")

    diagnoser = await Diagnoser.create()
    logger.info("[PIPELINE] ✓ Diagnoser ready (connected to Azure AI Foundry)")

    fixer = FixerAgent()
    logger.info("[PIPELINE] ✓ Fixer ready")

    logger.info("[PIPELINE] All agents initialized — entering monitoring loop")
    print()
    print("  Pipeline is LIVE — waiting for incidents...")
    print("  (Inject a failure: python -m simulator.failure_injector db_crash)")
    print("  Press Ctrl+C to stop.")
    print()

    incident_count = 0

    try:
        while True:
            # ── Phase 1: DETECT ──────────────────────────────────────────
            error_event = await watchman.monitor()
            incident_count += 1

            print()
            logger.info(
                "=" * 60
            )
            logger.info(
                "[PIPELINE] INCIDENT #%d DETECTED | type=%s | id=%s",
                incident_count,
                error_event.error_type,
                error_event.event_id,
            )

            # Publish to event bus (for dashboard / other listeners)
            bus.publish(TOPIC_ERROR_DETECTED, error_event)

            # ── Phase 2: DIAGNOSE ────────────────────────────────────────
            logger.info("[PIPELINE] Phase: DIAGNOSING...")
            diagnosis = await diagnoser.analyze(error_event)
            bus.publish(TOPIC_ERROR_DIAGNOSED, diagnosis)

            logger.info(
                "[PIPELINE] Diagnosis: root_cause=%s | action=%s | confidence=%.2f",
                diagnosis.root_cause,
                diagnosis.recovery_action,
                diagnosis.confidence,
            )

            # ── Phase 3: FIX ─────────────────────────────────────────────
            logger.info("[PIPELINE] Phase: FIXING...")
            fix_result = await fixer.execute(diagnosis)
            bus.publish(TOPIC_ERROR_FIXED, fix_result)

            # ── Phase 4: RECORD ──────────────────────────────────────────
            logger.info("[PIPELINE] Phase: RECORDING...")
            record_incident(error_event, diagnosis, fix_result)

            # ── Summary ──────────────────────────────────────────────────
            if fix_result.success:
                logger.info(
                    "[PIPELINE] ✓ INCIDENT #%d RESOLVED in %dms | "
                    "root_cause=%s | action=%s",
                    incident_count,
                    fix_result.resolution_time_ms,
                    diagnosis.root_cause,
                    diagnosis.recovery_action,
                )
            else:
                logger.warning(
                    "[PIPELINE] ✗ INCIDENT #%d NOT RESOLVED | "
                    "action=%s | error=%s",
                    incident_count,
                    fix_result.action_taken,
                    fix_result.error_message,
                )

            logger.info("=" * 60)
            print()

    except asyncio.CancelledError:
        logger.info("[PIPELINE] Received cancellation — shutting down...")
    finally:
        await diagnoser.close()
        logger.info("[PIPELINE] Diagnoser client closed. Goodbye.")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point with graceful shutdown on Ctrl+C."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    task = loop.create_task(run_pipeline())

    # Handle Ctrl+C gracefully
    def _shutdown(sig, frame):
        logger.info("[PIPELINE] Ctrl+C received — stopping...")
        task.cancel()

    signal.signal(signal.SIGINT, _shutdown)

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()
        print("\n  Pipeline stopped. See data/pattern_memory.json for incident log.\n")
>>>>>>> 7164f4d6a6f74c682323897fbdace8cd9fae780d


if __name__ == "__main__":
    main()
