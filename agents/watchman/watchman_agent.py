# agents/watchman/watchman_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# WATCHMAN — Agent 1 of the SRE Flight Crew Pipeline
#
# Monitors logs/server.log for error patterns and emits ErrorEvent objects.
#
# CHANGE LOG (why the team stub was replaced):
#   The original stub (commit f96d66c) returned a HARDCODED ErrorEvent with
#   a fixed DB_CRASH message every time. This was useful for initial wiring
#   but cannot drive a real pipeline — the Watchman must actually read the
#   log file and detect errors dynamically.
#
#   What was preserved from the team's stub:
#     - The ErrorEvent dataclass contract (shared/schemas.py) — unchanged
#     - The event_id format: evt_YYYYMMDD_HHMMSS_NNN
#     - The class name: WatchmanAgent
#
#   What changed:
#     - Now reads SERVER_LOG_PATH as an async tail (file position tracking)
#     - Classifies error_type from actual log content via log_parser.py
#     - Debounces duplicate incidents (same error_type within 30s)
#     - Async interface: await watchman.monitor() blocks until error found
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from shared.schemas import ErrorEvent
from shared.config import SERVER_LOG_PATH, WATCHMAN_POLL_INTERVAL_SEC
from agents.watchman.log_parser import (
    parse_log_line,
    classify_error_type,
    assess_severity,
    is_error_line,
)


logger = logging.getLogger("sre.watchman")

# Debounce window: suppress duplicate incidents of the same error_type
# within this many seconds. Prevents the Watchman from flooding the
# pipeline with repeated alerts for the same ongoing crash.
DEBOUNCE_SECONDS = 30

# How many trailing log lines to include as raw_log_snippet context
SNIPPET_LINES = 20


class WatchmanAgent:
    """
    Agent 1 — Log monitor that detects server errors and emits ErrorEvents.

    Reads the mock server's log file (logs/server.log) by tracking the file
    position. On each poll cycle, reads new lines, scans for ERROR/FATAL
    patterns, and when found, builds a structured ErrorEvent.

    Usage:
        watchman = WatchmanAgent()
        event = await watchman.monitor()  # blocks until error detected
    """

    def __init__(
        self,
        log_path: Optional[Path] = None,
        poll_interval: Optional[float] = None,
    ) -> None:
        self._log_path = Path(log_path or SERVER_LOG_PATH)
        self._poll_interval = poll_interval or WATCHMAN_POLL_INTERVAL_SEC
        self._file_position: int = 0
        self._incident_counter: int = 0
        self._last_alert_time: dict[str, float] = {}  # error_type -> timestamp
        self._recent_lines: list[str] = []  # rolling buffer for snippet context

        logger.info(
            "[WATCHMAN] Initialized | log=%s | poll=%.1fs",
            self._log_path,
            self._poll_interval,
        )

    # ─── Public API ──────────────────────────────────────────────────────

    async def monitor(self) -> ErrorEvent:
        """
        Block until an error is detected in the log file.

        Polls the log file at WATCHMAN_POLL_INTERVAL_SEC intervals,
        reading new lines from the last known position. When an error
        pattern is found (and passes debounce), returns an ErrorEvent.

        Returns
        -------
        ErrorEvent
            Structured error event ready for the Diagnoser.
        """
        logger.info("[WATCHMAN] Monitoring started — watching %s", self._log_path)

        # If the log file doesn't exist yet, wait for it
        while not self._log_path.exists():
            logger.info(
                "[WATCHMAN] Log file not found yet, waiting... (%s)",
                self._log_path,
            )
            await asyncio.sleep(self._poll_interval)

        # Seek to end of file on first run (only monitor NEW entries)
        if self._file_position == 0:
            self._file_position = self._log_path.stat().st_size
            logger.info(
                "[WATCHMAN] Seeked to end of log (pos=%d) — monitoring new entries only",
                self._file_position,
            )

        while True:
            event = self._scan_for_errors()
            if event is not None:
                return event
            await asyncio.sleep(self._poll_interval)

    def get_latest_error(self) -> Optional[ErrorEvent]:
        """
        Non-blocking scan: check for errors right now.

        Returns None if no new error is found. This preserves backward
        compatibility with code that called the team's original stub.
        """
        if not self._log_path.exists():
            return None
        return self._scan_for_errors()

    # ─── Internal: Log Scanning ──────────────────────────────────────────

    def _scan_for_errors(self) -> Optional[ErrorEvent]:
        """
        Read new lines from the log file and check for error patterns.
        Returns an ErrorEvent if a new (non-debounced) error is found.
        """
        try:
            current_size = self._log_path.stat().st_size
        except OSError:
            return None

        # Nothing new to read
        if current_size <= self._file_position:
            # Handle log rotation: if file shrunk, reset position
            if current_size < self._file_position:
                logger.info("[WATCHMAN] Log file rotated — resetting position")
                self._file_position = 0
            return None

        # Read new content
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._file_position)
                new_content = f.read()
                self._file_position = f.tell()
        except OSError as e:
            logger.warning("[WATCHMAN] Could not read log: %s", e)
            return None

        new_lines = new_content.splitlines()

        # Update rolling buffer for snippet context
        self._recent_lines.extend(new_lines)
        self._recent_lines = self._recent_lines[-SNIPPET_LINES:]

        # Scan for errors — process in order, return on first FATAL/ERROR match
        error_lines = []
        detected_type = None

        for line in new_lines:
            if not is_error_line(line):
                continue

            parsed = parse_log_line(line)
            if parsed is None:
                continue

            error_type = classify_error_type(parsed["message"])
            if error_type is None:
                continue

            error_lines.append(parsed)
            # Prefer the most specific error type (FATAL > ERROR level)
            if detected_type is None or parsed["level"] == "FATAL":
                detected_type = error_type

        if detected_type is None:
            return None

        # Debounce: skip if we already alerted for this error_type recently
        now = time.time()
        last_alert = self._last_alert_time.get(detected_type, 0)
        if now - last_alert < DEBOUNCE_SECONDS:
            logger.debug(
                "[WATCHMAN] Debounced %s (last alert %.0fs ago)",
                detected_type,
                now - last_alert,
            )
            return None

        # Build the ErrorEvent
        self._incident_counter += 1
        self._last_alert_time[detected_type] = now

        ts = datetime.now(timezone.utc)
        event_id = f"evt_{ts.strftime('%Y%m%d_%H%M%S')}_{self._incident_counter:03d}"

        # Build error message from the most severe line
        primary_line = error_lines[-1]  # last (usually FATAL) error
        error_message = primary_line["message"]

        # Build raw_log_snippet from recent lines for context
        raw_snippet = "\n".join(self._recent_lines[-SNIPPET_LINES:])

        event = ErrorEvent(
            event_id=event_id,
            timestamp=ts.isoformat(),
            error_type=detected_type,
            error_message=error_message,
            affected_service="mock_server",
            severity=assess_severity(detected_type),
            raw_log_snippet=raw_snippet,
        )

        logger.info(
            "[WATCHMAN] ERROR DETECTED | id=%s | type=%s | severity=%s",
            event.event_id,
            event.error_type,
            event.severity,
        )

        return event
