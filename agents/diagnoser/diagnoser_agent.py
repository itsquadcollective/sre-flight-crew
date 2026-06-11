from shared.schemas import ErrorEvent, DiagnosisResult


class DiagnoserAgent:
    def diagnose(self, event: ErrorEvent) -> DiagnosisResult:
        error_text = (event.error_message or "").lower()

        # Default fallback values
        root_cause = "unknown error"
        recommended_fix = "escalate_to_human"
        confidence = "low"

        # ---- Pattern matching ----
        if "timeout" in error_text:
            root_cause = "request timed out due to slow service or network delay"
            recommended_fix = "increase_timeout_or_check_network"
            confidence = "high"

        elif "connection refused" in error_text or "connection" in error_text:
            root_cause = "service or database connection failure"
            recommended_fix = "restart_service_or_check_db"
            confidence = "high"

        elif "not found" in error_text or "404" in error_text:
            root_cause = "requested resource does not exist"
            recommended_fix = "verify_endpoint_or_resource_path"
            confidence = "high"

        elif "permission denied" in error_text or "denied" in error_text:
            root_cause = "access permission issue"
            recommended_fix = "check_user_permissions_or_roles"
            confidence = "high"

        elif "null" in error_text or "none" in error_text:
            root_cause = "null or missing value caused runtime failure"
            recommended_fix = "validate_input_data"
            confidence = "medium"

        elif "database" in error_text:
            root_cause = "database-related failure"
            recommended_fix = "check_database_health_and_connections"
            confidence = "medium"

        # ---- Return structured result ----
        return DiagnosisResult(
            event_id=event.event_id,
            root_cause=root_cause,
            recommended_fix=recommended_fix,
            confidence=confidence
        )
