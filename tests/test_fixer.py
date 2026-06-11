import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from agents.fixer.fixer_agent import FixerAgent
from shared.schemas import DiagnosisResult, FixResult


@pytest.mark.anyio
async def test_fixer_escalate_to_human():
    fixer = FixerAgent(server_url="http://mock-server:8090", health_url="http://mock-server:8090/health")
    diagnosis = DiagnosisResult(
        event_id="evt_001",
        root_cause="unknown",
        confidence=0.2,
        recovery_action="escalate_to_human",
        script_path="",
        safety_confirmed=True,
        runbook_reference="",
        reasoning_summary="Low confidence."
    )
    result = await fixer.execute(diagnosis)
    assert result.success is False
    assert result.action_taken == "escalate_to_human"
    assert "Escalated to human" in result.error_message


@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
async def test_fixer_success_flow(mock_get, mock_post):
    # Setup mock responses
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"recovered": True}
    mock_post.return_value = mock_post_resp

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"status": "ok"}
    mock_get.return_value = mock_get_resp

    fixer = FixerAgent(server_url="http://mock-server:8090", health_url="http://mock-server:8090/health")
    diagnosis = DiagnosisResult(
        event_id="evt_001",
        root_cause="database_lock",
        confidence=0.9,
        recovery_action="restart_db",
        script_path="agents/fixer/recovery_scripts/restart_db.sh",
        safety_confirmed=True,
        runbook_reference="runbook_db_crash.md",
        reasoning_summary="Database deadlock detected."
    )
    
    result = await fixer.execute(diagnosis)
    assert result.success is True
    assert result.action_taken == "restart_db"
    assert result.health_check_status == 200
    
    mock_post.assert_called_once_with("http://mock-server:8090/sim/recover/restart_db")
    mock_get.assert_called_once_with("http://mock-server:8090/health")


@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
async def test_fixer_mismatch_409(mock_post):
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 409
    mock_post_resp.json.return_value = {"detail": "wrong recovery action"}
    mock_post.return_value = mock_post_resp

    fixer = FixerAgent(server_url="http://mock-server:8090", health_url="http://mock-server:8090/health")
    diagnosis = DiagnosisResult(
        event_id="evt_001",
        root_cause="database_lock",
        confidence=0.9,
        recovery_action="restart_db",
        script_path="",
        safety_confirmed=True,
        runbook_reference="",
        reasoning_summary="Restart DB requested."
    )

    result = await fixer.execute(diagnosis)
    assert result.success is False
    assert "wrong recovery action" in result.error_message


@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
async def test_fixer_unreachable_server(mock_post):
    mock_post.side_effect = httpx.ConnectError("Connection failed")

    fixer = FixerAgent(server_url="http://mock-server:8090", health_url="http://mock-server:8090/health")
    diagnosis = DiagnosisResult(
        event_id="evt_001",
        root_cause="database_lock",
        confidence=0.9,
        recovery_action="restart_db",
        script_path="",
        safety_confirmed=True,
        runbook_reference="",
        reasoning_summary="Restart DB requested."
    )

    result = await fixer.execute(diagnosis)
    assert result.success is False
    assert "unreachable" in result.error_message.lower()


@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
@patch("asyncio.sleep", new_callable=AsyncMock)  # bypass delay in test
async def test_fixer_health_timeout(mock_sleep, mock_get, mock_post):
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"recovered": True}
    mock_post.return_value = mock_post_resp

    # Health check returns 500 every time
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 500
    mock_get.return_value = mock_get_resp

    fixer = FixerAgent(server_url="http://mock-server:8090", health_url="http://mock-server:8090/health")
    diagnosis = DiagnosisResult(
        event_id="evt_001",
        root_cause="database_lock",
        confidence=0.9,
        recovery_action="restart_db",
        script_path="",
        safety_confirmed=True,
        runbook_reference="",
        reasoning_summary="Restart DB requested."
    )

    result = await fixer.execute(diagnosis)
    assert result.success is False
    assert result.health_check_status == 500
    assert mock_get.call_count == 5  # HEALTH_MAX_RETRIES
