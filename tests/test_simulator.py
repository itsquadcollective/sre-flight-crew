"""Infra tests: mock server crash/recover lifecycle (DevOps cell)."""
import pytest
from fastapi.testclient import TestClient

from simulator import mock_server
from simulator.mock_server import app


@pytest.fixture(autouse=True)
def fresh_state():
    mock_server.state = mock_server.ServerState()
    yield


client = TestClient(app)


def test_healthy_by_default():
    assert client.get("/health").status_code == 200
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/orders").status_code == 200


def test_db_crash_brings_server_down():
    r = client.post("/sim/inject/db_crash")
    assert r.status_code == 200
    assert r.json()["error_type"] == "DB_CRASH"
    health = client.get("/health")
    assert health.status_code == 500
    assert health.json()["error_type"] == "DB_CRASH"
    assert client.get("/api/orders").status_code == 500


def test_memory_spike_brings_server_down():
    client.post("/sim/inject/memory_spike")
    health = client.get("/health")
    assert health.status_code == 500
    assert health.json()["error_type"] == "MEMORY_SPIKE"


def test_correct_recovery_restores_service():
    client.post("/sim/inject/db_crash")
    r = client.post("/sim/recover/restart_db")
    assert r.status_code == 200
    assert r.json()["recovered"] is True
    assert client.get("/health").status_code == 200


def test_wrong_recovery_action_is_rejected():
    client.post("/sim/inject/db_crash")
    r = client.post("/sim/recover/clear_cache")
    assert r.status_code == 409
    assert r.json()["recovered"] is False
    assert client.get("/health").status_code == 500  # still down


def test_unknown_failure_and_action_rejected():
    assert client.post("/sim/inject/alien_invasion").status_code == 400
    assert client.post("/sim/recover/turn_it_off_and_on").status_code == 400


def test_state_endpoint_tracks_counts():
    client.post("/sim/inject/db_crash")
    client.post("/sim/recover/restart_db")
    s = client.get("/sim/state").json()
    assert s == {"healthy": True, "active_failure": None, "error_type": None,
                 "crash_count": 1, "recovery_count": 1}


def test_failure_writes_diagnosable_logs(tmp_path):
    client.post("/sim/inject/memory_spike")
    log_text = mock_server.SERVER_LOG_PATH.read_text()
    assert "MEMORY_SPIKE" in log_text
    assert "FATAL" in log_text
