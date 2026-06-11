import subprocess
import time
import shutil
import os
from pathlib import Path
import requests
from datetime import datetime, timezone
from shared.schemas import DiagnosisResult, FixResult

HEALTH_URL = os.getenv("HEALTH_CHECK_URL", "http://localhost:8090/health")

def find_bash() -> str:
    """Locate bash.exe — works whether or not Git Bash is on PATH."""
    found = shutil.which('bash')
    if found:
        return found
    # Derive from git's own location (bash ships with Git for Windows)
    git = shutil.which('git')
    if git:
        candidate = Path(git).parent.parent / 'bin' / 'bash.exe'
        if candidate.exists():
            return str(candidate)
    # Common install locations as last resort
    for c in [r'C:\Program Files\Git\bin\bash.exe',
              r'C:\Program Files (x86)\Git\bin\bash.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\bin\bash.exe')]:
        if os.path.exists(c):
            return c
    raise FileNotFoundError('bash.exe not found — install Git for Windows')

BASH = find_bash()


class FixerAgent:
    def execute_fix(self, diagnosis: DiagnosisResult) -> FixResult:
        start = time.perf_counter()

        # Safety gate — never act without confirmation
        if not diagnosis.safety_confirmed:
            return self._result(diagnosis, start, action='BLOCKED — safety not confirmed',
                                success=False, status=0,
                                error='Diagnosis was not safety-confirmed; human intervention required')

        # 1. Execute the approved recovery script
        try:
            proc = subprocess.run(
                [BASH, diagnosis.script_path],
                capture_output=True, text=True, timeout=30, check=True
            )
            action = f'Executed {diagnosis.script_path}'
            print(proc.stdout)
        except subprocess.CalledProcessError as e:
            return self._result(diagnosis, start, action=f'Script failed: {diagnosis.script_path}',
                                success=False, status=0, error=e.stderr or str(e))
        except subprocess.TimeoutExpired:
            return self._result(diagnosis, start, action=f'Script timed out: {diagnosis.script_path}',
                                success=False, status=0, error='Recovery script exceeded 30s timeout')

        # 2. Verify recovery via health check (retry up to 5 times)
        status = 0
        for _ in range(5):
            try:
                status = requests.get(HEALTH_URL, timeout=2).status_code
                if status == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)

        success = (status == 200)
        return self._result(diagnosis, start, action=action, success=success, status=status,
                            error='' if success else f'Health check failed with HTTP {status}')

    def _result(self, diagnosis, start, action, success, status, error):
        return FixResult(
            event_id=diagnosis.event_id,
            action_taken=action,
            success=success,
            health_check_status=status,
            resolution_time_ms=int((time.perf_counter() - start) * 1000),
            timestamp_resolved=datetime.now(timezone.utc).isoformat(),
            error_message=error
        )