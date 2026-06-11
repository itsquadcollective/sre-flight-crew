import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.diagnoser.diagnoser_agent import Diagnoser
from shared.schemas import ErrorEvent


def test_diagnoser_clean_and_parse_response():
    # Instantiate with dummy mocks since we are only testing synchronous helpers
    diagnoser = Diagnoser(
        project_client=MagicMock(),
        openai_client=MagicMock(),
        credential=MagicMock(),
        agent_name="DIAGNOSER",
        agent_version="5"
    )

    # Test markdown code block removal
    raw_markdown = '```json\n{"root_cause": "database_lock", "confidence": 0.9, "recovery_action": "restart_db"}\n```'
    parsed = diagnoser._parse_response(raw_markdown)
    assert parsed["root_cause"] == "database_lock"
    assert parsed["confidence"] == 0.9

    # Test citation annotation removal
    raw_citations = '{"root_cause": "memory_overflow", "confidence": 0.85, "recovery_action": "clear_cache", "thinking_trace": "found in logs【4:0†source】"}'
    parsed_citations = diagnoser._parse_response(raw_citations)
    assert parsed_citations["thinking_trace"] == "found in logs"


def test_diagnoser_validation_logic():
    diagnoser = Diagnoser(
        project_client=MagicMock(),
        openai_client=MagicMock(),
        credential=MagicMock(),
        agent_name="DIAGNOSER",
        agent_version="5"
    )

    # Valid scenario
    valid_data = {
        "root_cause": "database_lock",
        "confidence": 0.9,
        "recovery_action": "restart_db",
        "severity": "HIGH",
        "thinking_trace": "All good."
    }
    validated = diagnoser._validate_diagnosis(valid_data)
    assert validated["root_cause"] == "database_lock"
    assert validated["recovery_action"] == "restart_db"
    assert validated["confidence"] == 0.9

    # Unknown root cause -> default to service_crash
    unknown_rc = {
        "root_cause": "aliens_attacked",
        "confidence": 0.8,
        "recovery_action": "restart_db"
    }
    validated_rc = diagnoser._validate_diagnosis(unknown_rc)
    assert validated_rc["root_cause"] == "service_crash"

    # Unknown recovery action -> default to escalate_to_human
    unknown_act = {
        "root_cause": "database_lock",
        "confidence": 0.8,
        "recovery_action": "format_c_drive"
    }
    validated_act = diagnoser._validate_diagnosis(unknown_act)
    assert validated_act["recovery_action"] == "escalate_to_human"

    # Low confidence -> override to escalate_to_human
    low_conf = {
        "root_cause": "database_lock",
        "confidence": 0.4, # threshold is 0.6
        "recovery_action": "restart_db"
    }
    validated_lc = diagnoser._validate_diagnosis(low_conf)
    assert validated_lc["recovery_action"] == "escalate_to_human"

    # Clamp confidence
    clamp_high = {"root_cause": "database_lock", "confidence": 1.5, "recovery_action": "restart_db"}
    validated_ch = diagnoser._validate_diagnosis(clamp_high)
    assert validated_ch["confidence"] == 1.0


@pytest.mark.anyio
@patch("agents.diagnoser.diagnoser_agent.Diagnoser._load_pattern_history")
async def test_diagnoser_analyze_mock_flow(mock_pattern_history):
    mock_pattern_history.return_value = None

    # Mock the AsyncOpenAI client structures
    mock_openai = MagicMock()
    mock_openai.responses = MagicMock()
    mock_openai.responses.create = AsyncMock()
    
    # Mock response object containing output_text
    response_mock = MagicMock()
    response_mock.output_text = '{"root_cause": "database_lock", "confidence": 0.95, "recovery_action": "restart_db", "thinking_trace": "Confirmed deadlock from log search."}'
    mock_openai.responses.create.return_value = response_mock

    diagnoser = Diagnoser(
        project_client=MagicMock(),
        openai_client=mock_openai,
        credential=MagicMock(),
        agent_name="DIAGNOSER",
        agent_version="5"
    )

    test_event = ErrorEvent(
        event_id="evt_001",
        timestamp="2026-06-11T12:00:00Z",
        error_type="DB_CRASH",
        error_message="deadlock",
        affected_service="postgres",
        severity="critical",
        raw_log_snippet="ERROR deadlock"
    )

    result = await diagnoser.analyze(test_event)
    assert result.event_id == "evt_001"
    assert result.root_cause == "database_lock"
    assert result.confidence == 0.95
    assert result.recovery_action == "restart_db"
    assert "Confirmed deadlock" in result.reasoning_summary
