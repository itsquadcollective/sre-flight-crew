import pytest
import time
from pathlib import Path
from agents.watchman.log_parser import (
    parse_log_line,
    classify_error_type,
    assess_severity,
    is_error_line,
)
from agents.watchman.watchman_agent import WatchmanAgent
from shared.schemas import ErrorEvent


def test_is_error_line():
    assert is_error_line("2026-06-11T12:00:00+0000 ERROR [db] deadlock") is True
    assert is_error_line("2026-06-11T12:00:00+0000 FATAL [api] crash") is True
    assert is_error_line("2026-06-11T12:00:00+0000 INFO [api] normal request") is False


def test_parse_log_line():
    assert parse_log_line("") is None
    assert parse_log_line("   ") is None
    
    parsed = parse_log_line("2026-06-11T12:00:00+0000 ERROR [db-pool] deadlock detected")
    assert parsed is not None
    assert parsed["timestamp"] == "2026-06-11T12:00:00+0000"
    assert parsed["level"] == "ERROR"
    assert parsed["message"] == "ERROR [db-pool] deadlock detected"

    parsed_fatal = parse_log_line("2026-06-11T12:00:00+0000 FATAL service DOWN")
    assert parsed_fatal is not None
    assert parsed_fatal["level"] == "FATAL"


def test_classify_error_type():
    assert classify_error_type("ERROR [db-pool] deadlock detected") == "DB_CRASH"
    assert classify_error_type("WARN [cache] heap 98% full") == "MEMORY_SPIKE"
    assert classify_error_type("FATAL [api] worker unresponsive") == "MEMORY_SPIKE"
    assert classify_error_type("GET /health -> 500 (HTTP_500)") == "HTTP_500"
    assert classify_error_type("GET / 200 OK") is None


def test_assess_severity():
    assert assess_severity("DB_CRASH") == "critical"
    assert assess_severity("MEMORY_SPIKE") == "critical"


def test_watchman_agent_scanning(tmp_path):
    log_file = tmp_path / "server.log"
    # Create empty log file
    log_file.write_text("")

    agent = WatchmanAgent(log_path=log_file, poll_interval=0.1)
    
    # Initialize file position to end
    assert agent._file_position == 0
    # Scan should return None initially
    assert agent.get_latest_error() is None
    assert agent._file_position == 0

    # Append info line
    with open(log_file, "a") as f:
        f.write("2026-06-11T12:00:01+0000 INFO [api] request processed\n")

    # Scan info line should return None
    assert agent.get_latest_error() is None

    # Append error line
    with open(log_file, "a") as f:
        f.write("2026-06-11T12:00:02+0000 FATAL [api] DB_CRASH - database deadlock detected\n")

    # Scan should detect error
    event = agent.get_latest_error()
    assert event is not None
    assert isinstance(event, ErrorEvent)
    assert event.error_type == "DB_CRASH"
    assert "deadlock detected" in event.error_message
    assert event.severity == "critical"

    # Subsequent scan should return None (nothing new)
    assert agent.get_latest_error() is None

    # Debouncing check: append same error type immediately
    with open(log_file, "a") as f:
        f.write("2026-06-11T12:00:03+0000 FATAL [api] DB_CRASH - another deadlock\n")
    
    # Scan should return None due to debounce
    assert agent.get_latest_error() is None
