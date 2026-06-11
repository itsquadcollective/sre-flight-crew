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


if __name__ == "__main__":
    main()
