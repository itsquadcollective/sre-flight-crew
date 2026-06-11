# Standalone Fixer test — requires mock_server.py running in another terminal
from shared.schemas import DiagnosisResult
from agents.fixer.fixer_agent import FixerAgent

fake_diagnosis = DiagnosisResult(
    event_id='evt_test_001',
    root_cause='PostgreSQL container ran out of memory and crashed',
    confidence=0.94,
    recovery_action='restart_db',
    script_path='agents/fixer/recovery_scripts/restart_db.sh',
    safety_confirmed=True,
    runbook_reference='runbook_db_crash.md §3.2',
    reasoning_summary='Test diagnosis'
)

result = FixerAgent().execute_fix(fake_diagnosis)
print(result.to_json())
assert result.success, 'FIXER TEST FAILED'
print('\nFIXER TEST PASSED ✅')