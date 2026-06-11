from shared.schemas import ErrorEvent
from datetime import datetime, timezone

class WatchmanAgent:
    def get_latest_error(self) -> ErrorEvent:
        return ErrorEvent(
            event_id=f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_001",
            timestamp=datetime.now(timezone.utc).isoformat(),
            error_type="DB_CRASH",
            error_message="OperationalError: could not connect to server: Connection refused (PostgreSQL port 5432)",
            affected_service="db_container",
            severity="critical",
            raw_log_snippet="[14:32:03] ERROR db_container: connection refused port 5432\n[14:32:04] ERROR web_server: 500 Internal Server Error"
        )
