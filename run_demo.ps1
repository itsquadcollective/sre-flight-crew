# run_demo.ps1 — one-command demo launcher (DevOps cell)
# Usage:
#   .\run_demo.ps1            # start server + pipeline, inject manually
#   .\run_demo.ps1 -Demo      # also auto-inject db_crash after 5s
#   .\run_demo.ps1 -Demo -Failure memory_spike
param(
    [switch]$Demo,
    [ValidateSet("db_crash", "memory_spike")]
    [string]$Failure = "db_crash"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "✗ .venv not found — run setup first (docs/DEV_SETUP.md)"; exit 1 }

# 1. Start the target server in its own window
Write-Host "[demo] starting QuadShop target server on :8090 ..."
$uvicorn = Join-Path $root ".venv\Scripts\uvicorn.exe"
Start-Process -FilePath $uvicorn -ArgumentList "simulator.mock_server:app", "--port", "8090" -WorkingDirectory $root

# 2. Wait for /health to come up (max 30s)
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8090/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) { Write-Host "✗ server did not come up within 30s"; exit 1 }
Write-Host "[demo] ✓ server healthy"

# 3. Schedule auto-injection if -Demo
if ($Demo) {
    Write-Host "[demo] will inject '$Failure' in 5 seconds..."
    Start-Job -ScriptBlock {
        param($f)
        Start-Sleep -Seconds 5
        Invoke-WebRequest -Uri "http://127.0.0.1:8090/sim/inject/$f" -Method POST -UseBasicParsing | Out-Null
    } -ArgumentList $Failure | Out-Null
}

# 4. Run the pipeline in this window (Ctrl+C to stop)
Write-Host "[demo] starting pipeline..."
& $py (Join-Path $root "main.py")
