# agents/diagnoser/diagnoser_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSER — Agent 2 of the SRE Flight Crew Pipeline
#
# Uses azure-ai-projects v2.x → get_openai_client() → standard OpenAI
# Assistants API (beta.threads, beta.threads.runs, beta.threads.messages).
#
# Architecture (Foundry + OpenAI Assistants API):
#   1. Create a thread for the incident
#   2. Add the incident data as a user message
#   3. Create a run — the assistant processes using its instructions + file search
#   4. Read the assistant's response from the thread
#
# All operations are fully async.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

from shared.schemas import ErrorEvent, DiagnosisResult
from shared.config import (
    AZURE_PROJECT_ENDPOINT,
    DIAGNOSER_AGENT_NAME,
    DIAGNOSER_AGENT_VERSION,
    DIAGNOSER_ESCALATION_THRESHOLD,
    PATTERN_MEMORY_PATH,
)
from agents.diagnoser.prompt_templates import build_incident_message


# ─── Logger ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("sre.diagnoser")


# ─── Valid values for schema enforcement ─────────────────────────────────────
VALID_ROOT_CAUSES = {
    "database_lock", "memory_overflow", "port_conflict",
    "service_crash", "cascading_failure", "application_error",
    "timeout", "full_crash", "cache_failure",
}
VALID_ACTIONS = {
    "restart_db", "clear_cache", "restart_service",
    "scale_memory", "escalate_to_human",
}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class Diagnoser:
    """
    Agent 2 — Root-cause analysis via Azure AI Foundry + OpenAI Assistants API.

    The assistant is pre-deployed in Foundry with its instructions, file search
    tool, and runbook vector store. This class handles:
      - Creating threads per incident
      - Sending the incident data as a message
      - Running the assistant and waiting for completion
      - Parsing and validating the response

    Uses ``AIProjectClient.get_openai_client()`` to get an authenticated
    ``AsyncOpenAI`` client pointed at the Foundry project endpoint.

    Lifecycle:
        1. Call ``Diagnoser.create()`` to get an initialized instance.
        2. Call ``await diagnoser.analyze(error_event)`` per incident.
        3. Call ``await diagnoser.close()`` on shutdown to release resources.
    """

    def __init__(
        self,
        project_client: AIProjectClient,
        openai_client: AsyncOpenAI,
        credential: DefaultAzureCredential,
        agent_name: str,
        agent_version: str,
    ) -> None:
        self._project_client = project_client
        self._client = openai_client
        self._credential = credential
        self._agent_name = agent_name
        self._agent_version = agent_version

    @classmethod
    async def create(cls) -> "Diagnoser":
        """
        Factory method — initializes the Foundry project client, gets an
        authenticated OpenAI client, and returns a ready-to-use Diagnoser.
        """
        logger.info("[DIAGNOSER] Initializing Foundry → OpenAI client...")

        if not AZURE_PROJECT_ENDPOINT:
            raise ValueError(
                "AZURE_PROJECT_ENDPOINT not set in .env — "
                "cannot connect to Azure AI Foundry"
            )

        credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=AZURE_PROJECT_ENDPOINT,
            credential=credential,
        )

        # Get authenticated AsyncOpenAI client from Foundry project
        openai_client = project_client.get_openai_client()

        logger.info(
            "[DIAGNOSER] Connected to Foundry | agent_name=%s | version=%s",
            DIAGNOSER_AGENT_NAME,
            DIAGNOSER_AGENT_VERSION,
        )

        return cls(
            project_client=project_client,
            openai_client=openai_client,
            credential=credential,
            agent_name=DIAGNOSER_AGENT_NAME,
            agent_version=DIAGNOSER_AGENT_VERSION,
        )

    async def close(self) -> None:
        """Release the async clients and credential resources."""
        await self._client.close()
        await self._project_client.close()
        await self._credential.close()
        logger.info("[DIAGNOSER] Clients closed.")

    # ─── Public API ──────────────────────────────────────────────────────────

    async def analyze(self, error_event: ErrorEvent) -> DiagnosisResult:
        """
        Perform root-cause analysis on an incoming error event.

        Creates a new thread via the OpenAI Assistants API, sends the incident
        as a user message, runs the pre-deployed assistant, and returns
        the structured diagnosis.

        Parameters
        ----------
        error_event : ErrorEvent
            The structured error event produced by the Watchman agent.

        Returns
        -------
        DiagnosisResult
            Structured diagnosis with thinking trace, root cause, confidence,
            recommended action, and safety confirmation.
        """
        logger.info("=" * 60)
        logger.info(
            "[DIAGNOSER] Analyzing incident %s | type=%s | severity=%s",
            error_event.event_id,
            error_event.error_type,
            error_event.severity,
        )

        start_time = time.time()

        try:
            # Step 1: Build the incident message
            pattern_history = self._load_pattern_history()
            user_message = build_incident_message(
                error_event_json=error_event.to_json(),
                pattern_history=pattern_history,
            )

            # Step 2: Call the Responses API directly
            logger.info("[DIAGNOSER] Calling Responses API via agent_reference...")
            response = await self._client.responses.create(
                input=[{"role": "user", "content": user_message}],
                extra_body={
                    "agent_reference": {
                        "name": self._agent_name,
                        "version": self._agent_version,
                        "type": "agent_reference",
                    }
                },
            )

            # Step 3: Extract and parse the response content
            raw_response = response.output_text
            logger.info("[DIAGNOSER] Responses API returned successfully")
            diagnosis_data = self._parse_response(raw_response)

        except Exception as e:
            logger.error(
                "[DIAGNOSER] Foundry Agent call failed: %s — escalating to human",
                e,
            )
            return self._build_fallback_result(error_event, str(e))

        elapsed = round(time.time() - start_time, 2)

        # Step 6: Validate and build the typed result
        diagnosis_data = self._validate_diagnosis(diagnosis_data)

        result = DiagnosisResult(
            event_id=error_event.event_id,
            root_cause=diagnosis_data["root_cause"],
            confidence=diagnosis_data["confidence"],
            recovery_action=diagnosis_data["recovery_action"],
            script_path=self._resolve_script_path(diagnosis_data["recovery_action"]),
            safety_confirmed=diagnosis_data.get("safety_confirmed", True),
            runbook_reference=diagnosis_data.get("runbook_reference", ""),
            reasoning_summary=diagnosis_data.get("thinking_trace", ""),
        )

        logger.info(
            "[DIAGNOSER] Diagnosis complete in %.2fs | root_cause=%s | "
            "confidence=%.2f | action=%s",
            elapsed,
            result.root_cause,
            result.confidence,
            result.recovery_action,
        )
        logger.info(
            "[DIAGNOSER] Thinking trace preview: %s...",
            result.reasoning_summary[:200],
        )
        logger.info("=" * 60)

        return result

    # ─── Thread Message Extraction ───────────────────────────────────────────

    async def _extract_response(self, thread_id: str) -> str:
        """
        Read the assistant's response from the thread messages.

        After a run completes, the assistant's response is the last assistant
        message in the thread.
        """
        messages = await self._client.beta.threads.messages.list(
            thread_id=thread_id,
            order="desc",
            limit=5,
        )

        # Walk messages to find the last assistant response
        for msg in messages.data:
            if msg.role == "assistant":
                for content_block in msg.content:
                    if content_block.type == "text":
                        response_text = content_block.text.value
                        logger.info(
                            "[DIAGNOSER] Response extracted — %d characters",
                            len(response_text),
                        )
                        return response_text

        raise ValueError(
            "No assistant text response found in thread after run completion"
        )

    # ─── Response Parsing ────────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> dict:
        """
        Parse the AI response as JSON. Handles edge cases:
          - Markdown code fences (```json ... ```)
          - File-search citation annotations (【4:0†source】)
          - Leading/trailing whitespace
        """
        cleaned = raw.strip()

        # Strip markdown code fence if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        # Strip file-search citation annotations like 【4:0†source】
        cleaned = re.sub(r'【[^】]*】', '', cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "[DIAGNOSER] JSON parse failed: %s | Raw: %s", e, raw[:500]
            )
            raise ValueError(f"Diagnoser returned invalid JSON: {e}") from e

        return data

    # ─── Validation ──────────────────────────────────────────────────────────

    def _validate_diagnosis(self, data: dict) -> dict:
        """
        Validate and normalize the AI-generated diagnosis against known
        schema values. Clamp unknowns to safe defaults.
        """
        # Validate root_cause
        if data.get("root_cause") not in VALID_ROOT_CAUSES:
            logger.warning(
                "[DIAGNOSER] Unknown root_cause '%s' — defaulting to 'service_crash'",
                data.get("root_cause"),
            )
            data["root_cause"] = "service_crash"

        # Validate recovery_action
        if data.get("recovery_action") not in VALID_ACTIONS:
            logger.warning(
                "[DIAGNOSER] Unknown recovery_action '%s' — defaulting to 'escalate_to_human'",
                data.get("recovery_action"),
            )
            data["recovery_action"] = "escalate_to_human"

        # Validate severity
        if data.get("severity") not in VALID_SEVERITIES:
            data["severity"] = "HIGH"

        # Clamp confidence to [0.0, 1.0]
        confidence = data.get("confidence", 0.5)
        data["confidence"] = max(0.0, min(1.0, float(confidence)))

        # Auto-escalate if confidence is below threshold
        if data["confidence"] < DIAGNOSER_ESCALATION_THRESHOLD:
            logger.warning(
                "[DIAGNOSER] Low confidence (%.2f) — overriding to escalate_to_human",
                data["confidence"],
            )
            data["recovery_action"] = "escalate_to_human"

        # Ensure required string fields exist
        data.setdefault("thinking_trace", "No thinking trace produced.")
        data.setdefault("reasoning_steps", [])
        data.setdefault("runbook_reference", "")
        data.setdefault("safety_confirmed", True)

        return data

    # ─── Pattern History ─────────────────────────────────────────────────────

    def _load_pattern_history(self) -> Optional[str]:
        """
        Load the last 5 incidents from pattern_memory.json so the Diagnoser
        can detect recurring patterns and adjust severity accordingly.
        """
        try:
            memory_path = Path(PATTERN_MEMORY_PATH)
            if not memory_path.exists():
                return None

            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            incidents = data.get("incidents", [])
            if not incidents:
                return None

            recent = incidents[-5:]
            return json.dumps(recent, indent=2)

        except Exception as e:
            logger.warning("[DIAGNOSER] Could not load pattern history: %s", e)
            return None

    # ─── Script Path Resolution ──────────────────────────────────────────────

    @staticmethod
    def _resolve_script_path(action: str) -> str:
        """
        Map a recovery_action to the corresponding script path in the
        recovery_scripts/ directory.
        """
        SCRIPT_MAP = {
            "restart_db": "agents/fixer/recovery_scripts/restart_db.sh",
            "clear_cache": "agents/fixer/recovery_scripts/clear_cache.sh",
            "restart_service": "agents/fixer/recovery_scripts/restart_service.sh",
            "scale_memory": "agents/fixer/recovery_scripts/scale_memory.sh",
            "escalate_to_human": "",
        }
        return SCRIPT_MAP.get(action, "")

    # ─── Fallback Result ─────────────────────────────────────────────────────

    @staticmethod
    def _build_fallback_result(event: ErrorEvent, error_msg: str) -> DiagnosisResult:
        """
        Build a safe fallback DiagnosisResult when the agent call fails.
        Escalates to human and logs the failure reason.
        """
        return DiagnosisResult(
            event_id=event.event_id,
            root_cause="service_crash",
            confidence=0.0,
            recovery_action="escalate_to_human",
            script_path="",
            safety_confirmed=False,
            runbook_reference="FALLBACK — Agent call failed",
            reasoning_summary=(
                f"[DIAGNOSER FALLBACK] The Foundry Agent failed with error: "
                f"{error_msg}. This incident has been escalated to a human operator. "
                f"Original error type: {event.error_type}, "
                f"service: {event.affected_service}."
            ),
        )


# ─── Standalone smoke test ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    test_event = ErrorEvent(
        event_id="test-001",
        timestamp="2026-06-11T03:14:22Z",
        error_type="DB_CRASH",
        error_message="DB_LOCK: Connection pool exhausted - cannot acquire lock",
        affected_service="postgres",
        severity="critical",
        raw_log_snippet=(
            "2026-06-11T03:14:20Z [INFO]     Request GET / - 200 OK\n"
            "2026-06-11T03:14:22Z [ERROR]    DB_LOCK: Connection pool exhausted\n"
            "2026-06-11T03:14:22Z [CRITICAL] HTTP 500 - Internal Server Error\n"
        ),
    )

    async def main():
        diagnoser = await Diagnoser.create()
        try:
            result = await diagnoser.analyze(test_event)
            print("\n" + "=" * 60)
            print("DIAGNOSIS RESULT:")
            print("=" * 60)
            print(result.to_json())
        finally:
            await diagnoser.close()

    asyncio.run(main())
