# ==============================================================================
# SRE Flight Crew — Team Onboarding & Azure RBAC Setup Script (PowerShell)
# ==============================================================================
#
# This script guides Windows developers through:
#   1. Checking/installing the Azure CLI (az)
#   2. Logging into Azure (az login)
#   3. Selecting the correct active Subscription
#   4. Setting up the local .env configuration
#   5. Creating/installing the Python Virtual Environment
#   6. Running a quick Azure AI Foundry sanity auth check
#
# Usage:
#   .\setup_azure.ps1
# ==============================================================================

# Enable UTF-8 encoding for output
$OutputEncoding = [System.Text.Encoding]::UTF8

# --- Colors ---
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"
$Blue = "Blue"

# --- Printing Helpers ---
function Write-Info ($msg) { Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Write-Success ($msg) { Write-Host "[SUCCESS] $msg" -ForegroundColor $Green -Bold }
function Write-Warn ($msg) { Write-Host "[WARNING] $msg" -ForegroundColor $Yellow }
function Write-ErrorMsg ($msg) { Write-Host "[ERROR] $msg" -ForegroundColor $Red }

function Write-Header ($title) {
    Write-Host "========================================================================" -ForegroundColor $Cyan
    Write-Host "  $title" -ForegroundColor $Cyan -Bold
    Write-Host "========================================================================" -ForegroundColor $Cyan
}

Write-Header "SRE Flight Crew — Azure Developer Onboarding (Windows)"

# ─── STEP 1: Prerequisite Checks ──────────────────────────────────────────────
Write-Info "Checking local system prerequisites..."

# Check Python
$pythonCmd = "python"
$pythonVer = & $pythonCmd --version 2>&1
if ($LASTEXITCODE -ne 0) {
    $pythonCmd = "python3"
    $pythonVer = & $pythonCmd --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Python is not installed or not in PATH. Please install Python 3.10+."
        exit 1
    }
}
Write-Success "Python detected: $pythonVer"

# Check Git
$gitVer = & git --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Git is not installed or not in PATH. Please install Git."
    exit 1
}
Write-Success "Git detected: $gitVer"

# Check Azure CLI
$azVer = & az --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Azure CLI (az) was not found on your system."
    $installCli = Read-Host "Would you like to install the Azure CLI via winget now? (Y/n)"
    if ([string]::IsNullOrEmpty($installCli) -or $installCli -match "^[Yy]$") {
        Write-Info "Installing Azure CLI via winget..."
        winget install Microsoft.AzureCLI --silent
        Write-Warn "Azure CLI installation started. You WILL need to restart your terminal or VS Code for the command to become available."
        exit 0
    } else {
        Write-Info "Please install the Azure CLI manually (https://aka.ms/installazurecliwindows) and run this script again."
        exit 1
    }
}
$cliVersionLine = ($azVer | Select-Object -First 1)
Write-Success "Azure CLI detected: $cliVersionLine"

# ─── STEP 2: Authenticate to Entra ID (az login) ──────────────────────────────
Write-Header "Step 2: Azure Authentication"

# Check if already logged in
Write-Info "Checking current login status..."
$showAccount = & az account show 2>$null
if ($LASTEXITCODE -eq 0) {
    $accountData = $showAccount | ConvertFrom-Json
    $currentUser = $accountData.user.name
    Write-Success "Already logged in as: $currentUser"
    $reLogin = Read-Host "Would you like to log in with a different account? [Y/n]"
    if ([string]::IsNullOrEmpty($reLogin) -or $reLogin -match "^[Yy]$") {
        Write-Info "Opening browser for interactive login..."
        az login
    }
} else {
    Write-Info "No active Azure session found. Launching login..."
    az login
}

# ─── STEP 3: Select Active Subscription ───────────────────────────────────────
Write-Header "Step 3: Subscription Selection"

Write-Info "Fetching your available subscriptions..."
az account list --output table

Write-Host ""
$selectedSub = Read-Host "Enter the Subscription ID or Name to target (or press Enter to keep default)"
if (-not [string]::IsNullOrEmpty($selectedSub)) {
    Write-Info "Setting active subscription..."
    az account set --subscription "$selectedSub"
    if ($LASTEXITCODE -eq 0) {
        $activeAccount = (& az account show | ConvertFrom-Json)
        Write-Success "Subscription active: $($activeAccount.name) ($($activeAccount.id))"
    } else {
        Write-ErrorMsg "Failed to set subscription. Proceeding with current default."
    }
} else {
    $activeAccount = (& az account show | ConvertFrom-Json)
    Write-Info "Using current default subscription: $($activeAccount.name)"
}

$subId = (& az account show --query "id" -o tsv).Trim()

# ─── STEP 4: Configure Local environment (.env) ───────────────────────────────
Write-Header "Step 4: Local Configuration (.env)"

$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Info "Creating .env file from .env.example..."
    Copy-Item ".env.example" ".env"
}

# Prompt user for project specifics
Write-Host "Please enter the Azure AI Foundry resources details provided by your Project Lead (or press Enter to use team defaults):" -ForegroundColor $Yellow
$projectEndpoint = Read-Host "Azure AI Project Endpoint [Default: https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam]"
if ([string]::IsNullOrEmpty($projectEndpoint)) {
    $projectEndpoint = "https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam"
}

$resourceGroup = Read-Host "Resource Group Name [Default: rg-ochuko]"
if ([string]::IsNullOrEmpty($resourceGroup)) {
    $resourceGroup = "rg-ochuko"
}

$modelName = Read-Host "Model Deployment Name [Default: gpt-4.1]"
if ([string]::IsNullOrEmpty($modelName)) {
    $modelName = "gpt-4.1"
}

$agentId = Read-Host "Diagnoser Agent ID (optional) [Default: none]"
if ([string]::IsNullOrEmpty($agentId)) {
    $agentId = "none"
}

$agentName = Read-Host "Diagnoser Agent Name [Default: DIAGNOSER]"
if ([string]::IsNullOrEmpty($agentName)) {
    $agentName = "DIAGNOSER"
}

$agentVersion = Read-Host "Diagnoser Agent Version [Default: 11]"
if ([string]::IsNullOrEmpty($agentVersion)) {
    $agentVersion = "11"
}

# Trim any whitespace
$projectEndpoint = $projectEndpoint.Trim()
$resourceGroup = $resourceGroup.Trim()
$modelName = $modelName.Trim()
$agentId = $agentId.Trim()
$agentName = $agentName.Trim()
$agentVersion = $agentVersion.Trim()

# Update .env using inline Python script for robust file modifications
Write-Info "Updating .env file variables..."
& $pythonCmd -c @"
import os
env_path = '.env'
updates = {
    'AZURE_PROJECT_ENDPOINT': '$projectEndpoint',
    'AZURE_SUBSCRIPTION_ID': '$subId',
    'AZURE_RESOURCE_GROUP': '$resourceGroup',
    'MODEL_DEPLOYMENT_NAME': '$modelName',
    'DIAGNOSER_AGENT_ID': '$agentId',
    'DIAGNOSER_AGENT_NAME': '$agentName',
    'DIAGNOSER_AGENT_VERSION': '$agentVersion'
}

lines = []
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

new_lines = []
keys_found = set()
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        k = k.strip()
        if k in updates and updates[k]:
            new_lines.append(f'{k}={updates[k]}\n')
            keys_found.add(k)
            continue
    new_lines.append(line)

for k, v in updates.items():
    if k not in keys_found and v:
        new_lines.append(f'{k}={v}\n')

with open(env_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Updated successfully.')
"@

Write-Success ".env file updated successfully."

# ─── STEP 5: Python Environment Setup ─────────────────────────────────────────
Write-Header "Step 5: Python Virtual Environment"

$setupVenv = Read-Host "Would you like to initialize/update the virtual environment (.venv)? [Y/n]"
if ([string]::IsNullOrEmpty($setupVenv) -or $setupVenv -match "^[Yy]$") {
    if (-not (Test-Path ".venv")) {
        Write-Info "Creating virtual environment (.venv)..."
        & $pythonCmd -m venv .venv
    }

    # Activate virtual environment and install packages
    Write-Info "Activating environment and installing dependencies..."
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        & .venv\Scripts\pip.exe install --upgrade pip
        & .venv\Scripts\pip.exe install -r requirements.txt
    } else {
        & .venv/bin/pip install --upgrade pip
        & .venv/bin/pip install -r requirements.txt
    }
    Write-Success "Dependencies installed successfully."
}

# ─── STEP 6: Run Azure AI Connection Check ────────────────────────────────────
Write-Header "Step 6: Azure AI Connection Verification"

$runCheck = Read-Host "Would you like to run a connection sanity check to verify your RBAC access? [Y/n]"
if ([string]::IsNullOrEmpty($runCheck) -or $runCheck -match "^[Yy]$") {
    Write-Info "Running verification script..."
    
    $checkScript = @"
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load env
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / '.env')

endpoint = os.getenv('AZURE_PROJECT_ENDPOINT')
deployment = os.getenv('MODEL_DEPLOYMENT_NAME', 'gpt-4.1')

if not endpoint:
    print('[ERROR] AZURE_PROJECT_ENDPOINT is not set in .env')
    sys.exit(1)

print(f'Connecting to endpoint: {endpoint}')
print(f'Using deployment: {deployment}')
print('Attempting authentication via DefaultAzureCredential...')

try:
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=endpoint,
        credential=credential
    )
    
    print('DefaultAzureCredential authenticated successfully!')
    print('Retrieving OpenAI client connection...')
    openai_client = client.get_openai_client()
    print('Success! Connection established.')
    print('==== AUTH_OK ====')
    
except Exception as e:
    print(f'\n[ERROR] Authentication or connection failed: {e}')
    print('\nPlease verify that:')
    print('  1. You ran \"az login\" with the correct account.')
    print('  2. Your account has the \"Azure AI Developer\" or \"Contributor\" role on the project resource group.')
    print('  3. The AZURE_PROJECT_ENDPOINT in your .env is correct.')
    sys.exit(1)
"@

    # Write temporary python test file
    New-Item -ItemType Directory -Path "scratch" -Force | Out-Null
    $checkScript | Out-File -FilePath "scratch\temp_azure_check.py" -Encoding utf8

    # Execute test script
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        & .venv\Scripts\python.exe scratch\temp_azure_check.py
    } else {
        & .venv/bin/python scratch/temp_azure_check.py
    }

    # Clean up
    Remove-Item "scratch\temp_azure_check.py" -ErrorAction SilentlyContinue
}

Write-Header "Setup Complete! You are ready to build."
Write-Info "To start the system:"
Write-Host "  1. Start the target mock server:  uvicorn simulator.mock_server:app --port 8090" -ForegroundColor $Cyan
Write-Host "  2. Start the recovery pipeline:   python main.py" -ForegroundColor $Cyan
Write-Host "  3. Inject a failure:              python -m simulator.failure_injector db_crash" -ForegroundColor $Cyan
Write-Host ""
