# agents/fixer/fixer_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# FIXER — Agent 3 of the SRE Flight Crew Pipeline
#
# Executes remediation actions prescribed by the Diagnoser agent.
#
# DESIGN DECISION — HTTP vs bash scripts:
#   The team's recovery_scripts/ directory contains bash scripts
#   (restart_db.sh, clear_cache.sh) that curl the mock server's
#   /sim/recover/{action} endpoint. On Windows, bash scripts require
#   Git Bash or WSL.
#
#   For cross-platform reliability, the Fixer calls the mock server's
#   HTTP API directly via aiohttp/httpx. The bash scripts are preserved
#   in the repo for reference and for Linux/macOS users who prefer them.
#
#   Both approaches achieve the same result: POST /sim/recover/{action}
#   on the mock server, which resets the server state to healthy.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from shared.schemas import DiagnosisResult, FixResult
from shared.config import MOCK_SERVER_URL, HEALTH_CHECK_URL


logger = logging.getLogger("sre.fixer")

# How many times to poll /health after recovery before giving up
HEALTH_MAX_RETRIES = 5
HEALTH_RETRY_DELAY = 2.0  # seconds between health checks


# Map recovery_action → mock server /sim/recover/{action} endpoint
ACTION_MAP = {
    "restart_db":       "restart_db",
    "clear_cache":      "clear_cache",
    "restart_service":  "restart_service",
    "scale_memory":     "clear_cache",  # closest available on mock server
}


class FixerAgent:
    """
    Agent 3 — Executes remediation and verifies recovery.

    Takes a DiagnosisResult from the Diagnoser, calls the mock server's
    recovery API, then confirms health is restored.

    Usage:
        fixer = FixerAgent()
        result = await fixer.execute(diagnosis)
    """

    def __init__(
        self,
        server_url: str | None = None,
        health_url: str | None = None,
    ) -> None:
        self._server_url = server_url or MOCK_SERVER_URL
        self._health_url = health_url or HEALTH_CHECK_URL

        logger.info(
            "[FIXER] Initialized | server=%s | health=%s",
            self._server_url,
            self._health_url,
        )

    async def execute(self, diagnosis: DiagnosisResult) -> FixResult:
        """
        Execute the prescribed recovery action and verify health.

        Parameters
        ----------
        diagnosis : DiagnosisResult
            The diagnosis from the Diagnoser agent, containing the
            recovery_action to execute.

        Returns
        -------
        FixResult
            Structured result with success status, timing, and details.
        """
        logger.info(
            "[FIXER] Executing recovery | event=%s | action=%s | confidence=%.2f",
            diagnosis.event_id,
            diagnosis.recovery_action,
            diagnosis.confidence,
        )

        start_time = time.time()

        # ── Handle escalation (no automated fix) ─────────────────────────
        if diagnosis.recovery_action == "escalate_to_human":
            logger.warning(
                "[FIXER] Action is 'escalate_to_human' — skipping automated recovery"
            )
            return FixResult(
                event_id=diagnosis.event_id,
                action_taken="escalate_to_human",
                success=False,
                health_check_status=0,
                resolution_time_ms=0,
                timestamp_resolved=datetime.now(timezone.utc).isoformat(),
                error_message="Escalated to human operator — no automated fix attempted",
            )

        # ── Map action to mock server endpoint ───────────────────────────
        action_key = ACTION_MAP.get(diagnosis.recovery_action)
        if action_key is None:
            logger.error(
                "[FIXER] Unknown recovery_action: %s", diagnosis.recovery_action
            )
            return self._build_failure(
                diagnosis,
                start_time,
                f"Unknown recovery_action: {diagnosis.recovery_action}",
            )

        # ── Execute recovery via HTTP ────────────────────────────────────
        recover_url = f"{self._server_url}/sim/recover/{action_key}"
        logger.info("[FIXER] POST %s", recover_url)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(recover_url)

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "[FIXER] Recovery API returned 200 | recovered=%s",
                    data.get("recovered"),
                )
            elif response.status_code == 409:
                # Wrong action for the active failure
                data = response.json()
                detail = data.get("detail", "action mismatch")
                logger.warning("[FIXER] Recovery mismatch (409): %s", detail)
                return self._build_failure(diagnosis, start_time, detail)
            else:
                logger.error(
                    "[FIXER] Recovery API returned %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return self._build_failure(
                    diagnosis,
                    start_time,
                    f"Recovery API returned HTTP {response.status_code}",
                )

        except httpx.ConnectError:
            logger.error(
                "[FIXER] Cannot reach mock server at %s — is it running?",
                self._server_url,
            )
            return self._build_failure(
                diagnosis, start_time, f"Mock server unreachable at {self._server_url}"
            )
        except Exception as e:
            logger.error("[FIXER] Recovery call failed: %s", e)
            return self._build_failure(diagnosis, start_time, str(e))

        # ── Verify health ────────────────────────────────────────────────
        health_status = await self._confirm_recovery()
        elapsed_ms = int((time.time() - start_time) * 1000)

        if health_status == 200:
            logger.info(
                "[FIXER] ✓ Recovery CONFIRMED | health=200 | elapsed=%dms",
                elapsed_ms,
            )
            return FixResult(
                event_id=diagnosis.event_id,
                action_taken=diagnosis.recovery_action,
                success=True,
                health_check_status=200,
                resolution_time_ms=elapsed_ms,
                timestamp_resolved=datetime.now(timezone.utc).isoformat(),
                error_message="",
            )
        else:
            logger.error(
                "[FIXER] ✗ Recovery FAILED — health returned %d after %d retries",
                health_status,
                HEALTH_MAX_RETRIES,
            )
            return FixResult(
                event_id=diagnosis.event_id,
                action_taken=diagnosis.recovery_action,
                success=False,
                health_check_status=health_status,
                resolution_time_ms=elapsed_ms,
                timestamp_resolved=datetime.now(timezone.utc).isoformat(),
                error_message=f"Health check returned {health_status} after recovery",
            )

    # ─── Health Check ────────────────────────────────────────────────────

    async def _confirm_recovery(self) -> int:
        """
        Poll the health endpoint until it returns 200 or retries are exhausted.

        Returns
        -------
        int
            The HTTP status code from the last health check attempt.
        """
        for attempt in range(1, HEALTH_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(self._health_url)
                    if resp.status_code == 200:
                        logger.info(
                            "[FIXER] Health check %d/%d: 200 OK",
                            attempt,
                            HEALTH_MAX_RETRIES,
                        )
                        return 200
                    logger.info(
                        "[FIXER] Health check %d/%d: %d (waiting...)",
                        attempt,
                        HEALTH_MAX_RETRIES,
                        resp.status_code,
                    )
            except Exception as e:
                logger.warning(
                    "[FIXER] Health check %d/%d failed: %s",
                    attempt,
                    HEALTH_MAX_RETRIES,
                    e,
                )

            if attempt < HEALTH_MAX_RETRIES:
                await asyncio.sleep(HEALTH_RETRY_DELAY)

        return 500  # Exhausted retries

    # ─── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_failure(
        diagnosis: DiagnosisResult,
        start_time: float,
        error_msg: str,
    ) -> FixResult:
        """Build a FixResult for a failed recovery attempt."""
        return FixResult(
            event_id=diagnosis.event_id,
            action_taken=diagnosis.recovery_action,
            success=False,
            health_check_status=0,
            resolution_time_ms=int((time.time() - start_time) * 1000),
            timestamp_resolved=datetime.now(timezone.utc).isoformat(),
            error_message=error_msg,
        )
