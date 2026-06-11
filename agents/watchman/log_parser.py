# agents/watchman/log_parser.py
# ─────────────────────────────────────────────────────────────────────────────
# Utility module for parsing mock server log lines.
#
# The mock_server.py writes structured lines to logs/server.log.
# This module extracts error information from those lines and classifies
# them into ErrorEvent-compatible types.
#
# Built to complement the team's mock_server.py log format.
# ─────────────────────────────────────────────────────────────────────────────

import re
from typing import Optional


# ─── Error type patterns ─────────────────────────────────────────────────────
# These patterns match the log output from simulator/mock_server.py FAILURES
# catalogue. They map log content to shared/schemas.py ErrorEvent.error_type.

ERROR_PATTERNS = [
    # Pattern                         error_type     severity
    (re.compile(r"DB_CRASH"),         "DB_CRASH",    "critical"),
    (re.compile(r"MEMORY_SPIKE"),     "MEMORY_SPIKE","critical"),
    (re.compile(r"SERVICE_CRASH"),    "SERVICE_CRASH","critical"),
    (re.compile(r"deadlock detected"),"DB_CRASH",    "critical"),
    (re.compile(r"connection.*timed out"), "DB_CRASH","warning"),
    (re.compile(r"heap \d+%"),        "MEMORY_SPIKE","warning"),
    (re.compile(r"allocation failures"), "MEMORY_SPIKE", "critical"),
    (re.compile(r"worker unresponsive"), "MEMORY_SPIKE", "critical"),
    (re.compile(r"-> 500"),           "HTTP_500",    "critical"),
    (re.compile(r"service DOWN"),     "DB_CRASH",    "critical"),
]


def parse_log_line(line: str) -> Optional[dict]:
    """
    Parse a single log line from the mock server.

    Expected format (from mock_server.py logging config):
        YYYY-MM-DDTHH:MM:SS+ZZZZ MESSAGE

    Parameters
    ----------
    line : str
        A single line from logs/server.log.

    Returns
    -------
    dict or None
        {"timestamp": str, "level": str, "message": str} if parseable,
        None if the line is empty or unparseable.
    """
    line = line.strip()
    if not line:
        return None

    # The mock_server uses: %(asctime)s %(message)s
    # asctime format: %Y-%m-%dT%H:%M:%S%z
    # The message itself contains the level prefix like "ERROR [db-pool] ..."
    parts = line.split(" ", 1)
    if len(parts) < 2:
        return None

    timestamp = parts[0]
    message = parts[1]

    # Extract level from message prefix (e.g., "ERROR [db-pool] ...")
    level = "INFO"
    for lvl in ("FATAL", "ERROR", "WARN", "INFO"):
        if message.lstrip().startswith(lvl):
            level = lvl
            break

    return {
        "timestamp": timestamp,
        "level": level,
        "message": message,
    }


def classify_error_type(message: str) -> Optional[str]:
    """
    Classify a log message into an ErrorEvent.error_type value.

    Scans the message against known error patterns from the mock server's
    FAILURES catalogue. Returns the first match.

    Parameters
    ----------
    message : str
        The message portion of a log line.

    Returns
    -------
    str or None
        The error_type string (e.g., "DB_CRASH", "MEMORY_SPIKE") or None
        if no error pattern is detected.
    """
    for pattern, error_type, _ in ERROR_PATTERNS:
        if pattern.search(message):
            return error_type
    return None


def assess_severity(error_type: str) -> str:
    """
    Determine severity based on error type.

    Parameters
    ----------
    error_type : str
        The classified error type.

    Returns
    -------
    str
        "critical" or "warning"
    """
    return "critical"


def is_error_line(line: str) -> bool:
    """
    Quick check: does this log line contain an error-level message?

    Used by the Watchman to skip INFO lines without full parsing overhead.

    Parameters
    ----------
    line : str
        A raw log line.

    Returns
    -------
    bool
        True if the line contains ERROR, FATAL, or a known error pattern.
    """
    upper = line.upper()
    return "ERROR" in upper or "FATAL" in upper
