# shared/schemas.py
# ─────────────────────────────────────────────────────────────────────────────
# THE TEAM CONTRACT — every agent imports from this file.
# Never define data structures inside your agent files.
# If you need to change a field, change it HERE and it updates everywhere.
# ─────────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass, asdict
from typing import Literal
import json


# ─── STEP 1 OF PIPELINE ──────────────────────────────────────────────────────
# Watchman creates this and sends it to the Diagnoser

@dataclass
class ErrorEvent:
    event_id: str
    timestamp: str
    error_type: Literal["HTTP_500", "HTTP_504", "MEMORY_SPIKE", "DB_CRASH", "CACHE_FAIL"]
    error_message: str
    affected_service: str
    severity: Literal["critical", "warning"]
    raw_log_snippet: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ─── STEP 2 OF PIPELINE ──────────────────────────────────────────────────────
# Diagnoser creates this and sends it to the Fixer

@dataclass
class DiagnosisResult:
    event_id: str
    root_cause: str
    confidence: float
    recovery_action: Literal["restart_db", "clear_cache", "restart_service", "scale_memory"]
    script_path: str
    safety_confirmed: bool
    runbook_reference: str
    reasoning_summary: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ─── STEP 3 OF PIPELINE ──────────────────────────────────────────────────────
# Fixer creates this and sends it to the Dashboard

@dataclass
class FixResult:
    event_id: str
    action_taken: str
    success: bool
    health_check_status: int
    resolution_time_ms: int
    timestamp_resolved: str
    error_message: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ─── DASHBOARD STATUS ─────────────────────────────────────────────────────────
# Dashboard reads this every 2 seconds to update the screen

@dataclass
class SystemStatus:
    status: Literal["healthy", "degraded", "incident", "recovering"]
    last_updated: str
    active_incident: bool
    current_event_id: str
    last_resolution_ms: int
    total_incidents_resolved: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)