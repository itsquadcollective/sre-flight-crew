#!/usr/bin/env bash
# ==============================================================================
# SRE Flight Crew — Team Onboarding & Azure RBAC Setup Script
# ==============================================================================
#
# This script guides developers through:
#   1. Checking/installing the Azure CLI (az)
#   2. Logging into Azure (az login)
#   3. Selecting the correct active Subscription
#   4. Setting up the local .env configuration
#   5. Creating/installing the Python Virtual Environment
#   6. Running a quick Azure AI Foundry sanity auth check
#
# Usage:
#   bash setup_azure.sh
# ==============================================================================

# --- Color Definitions ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0;68m' # No Color
BOLD='\033[1m'

# --- Printing Helpers ---
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} ${BOLD}$1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    echo -e "${CYAN}========================================================================${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}========================================================================${NC}"
}

header "SRE Flight Crew — Azure Developer Onboarding"

# ─── STEP 1: Prerequisite Checks ──────────────────────────────────────────────
info "Checking local system prerequisites..."

# Check Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    error "Python is not installed. Please install Python 3.10+ before running this script."
    exit 1
fi
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    PYTHON_CMD="python3"
fi
success "Python detected: $($PYTHON_CMD --version)"

# Check Git
if ! command -v git &> /dev/null; then
    error "Git is not installed. Please install Git before proceeding."
    exit 1
fi
success "Git detected: $(git --version)"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    warn "Azure CLI (az) was not found on your system."
    info "To install the Azure CLI, please run the corresponding command for your OS:"
    echo ""
    echo -e "  ${BOLD}Windows (Git Bash/PowerShell):${NC}"
    echo -e "    winget install Microsoft.AzureCLI"
    echo ""
    echo -e "  ${BOLD}macOS (Homebrew):${NC}"
    echo -e "    brew install azure-cli"
    echo ""
    echo -e "  ${BOLD}Linux (Debian/Ubuntu):${NC}"
    echo -e "    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    echo ""
    read -p "Would you like this script to attempt installing Azure CLI via winget/brew? (y/n): " install_cli
    if [[ $install_cli =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            info "Installing Azure CLI via winget..."
            winget install Microsoft.AzureCLI --silent
            warn "You may need to restart your terminal or shell for the 'az' command to become available."
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            info "Installing Azure CLI via Brew..."
            brew install azure-cli
        else
            info "Installing Azure CLI via official curl installer..."
            curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
        fi
    else
        info "Please install the Azure CLI manually and run this script again."
        exit 1
    fi

    # Re-check
    if ! command -v az &> /dev/null; then
        error "Azure CLI installation verification failed. Please restart your terminal and try again."
        exit 1
    fi
fi
success "Azure CLI detected: $(az --version | head -n 1)"

# ─── STEP 2: Authenticate to Entra ID (az login) ──────────────────────────────
header "Step 2: Azure Authentication"

# Check if already logged in
info "Checking current login status..."
if az account show &> /dev/null; then
    CURRENT_USER=$(az account show --query "user.name" -o tsv)
    success "Already logged in as: ${CURRENT_USER}"
    read -p "Would you like to log in with a different account? (y/n): " re_login
    if [[ $re_login =~ ^[Yy]$ ]]; then
        info "Opening browser for interactive login..."
        az login
    fi
else
    info "No active Azure session found. Launching login..."
    az login
fi

# ─── STEP 3: Select Active Subscription ───────────────────────────────────────
header "Step 3: Subscription Selection"

info "Fetching your available subscriptions..."
az account list --output table

echo ""
read -p "Enter the Subscription ID or Name to target: " SELECTED_SUB
if [ -n "$SELECTED_SUB" ]; then
    info "Setting active subscription..."
    if az account set --subscription "$SELECTED_SUB"; then
        success "Subscription active: $(az account show --query "name" -o tsv) ($(az account show --query "id" -o tsv))"
    else
        error "Failed to set subscription. Proceeding with default subscription."
    fi
else
    info "No subscription entered. Using current default: $(az account show --query "name" -o tsv)"
fi

# Retrieve subscription ID for .env (and strip potential carriage returns from Windows CLI)
SUB_ID=$(az account show --query "id" -o tsv | tr -d '\r')

# ─── STEP 4: Configure Local environment (.env) ───────────────────────────────
header "Step 4: Local Configuration (.env)"

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    info "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Prompt user for project specifics
echo -e "${YELLOW}Please enter the Azure AI Foundry resources details provided by your Project Lead (or press Enter to use team defaults):${NC}"
read -p "Azure AI Project Endpoint [Default: https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam]: " PROJECT_ENDPOINT
PROJECT_ENDPOINT=${PROJECT_ENDPOINT:-"https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam"}

read -p "Resource Group Name [Default: rg-ochuko]: " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-"rg-ochuko"}

read -p "Model Deployment Name [Default: gpt-4.1]: " MODEL_NAME
MODEL_NAME=${MODEL_NAME:-"gpt-4.1"}

read -p "Diagnoser Agent ID (optional) [Default: none]: " AGENT_ID
AGENT_ID=${AGENT_ID:-"none"}

read -p "Diagnoser Agent Name [Default: DIAGNOSER]: " AGENT_NAME
AGENT_NAME=${AGENT_NAME:-"DIAGNOSER"}

read -p "Diagnoser Agent Version [Default: 11]: " AGENT_VERSION
AGENT_VERSION=${AGENT_VERSION:-"11"}

# Strip potential carriage returns (\r) from user inputs on Windows
PROJECT_ENDPOINT=$(echo "$PROJECT_ENDPOINT" | tr -d '\r')
RESOURCE_GROUP=$(echo "$RESOURCE_GROUP" | tr -d '\r')
MODEL_NAME=$(echo "$MODEL_NAME" | tr -d '\r')
AGENT_ID=$(echo "$AGENT_ID" | tr -d '\r')
AGENT_NAME=$(echo "$AGENT_NAME" | tr -d '\r')
AGENT_VERSION=$(echo "$AGENT_VERSION" | tr -d '\r')

# Use inline Python script to update .env cleanly on all operating systems
info "Updating .env file variables..."
$PYTHON_CMD -c "
import os
env_path = '.env'
updates = {
    'AZURE_PROJECT_ENDPOINT': '$PROJECT_ENDPOINT',
    'AZURE_SUBSCRIPTION_ID': '$SUB_ID',
    'AZURE_RESOURCE_GROUP': '$RESOURCE_GROUP',
    'MODEL_DEPLOYMENT_NAME': '$MODEL_NAME',
    'DIAGNOSER_AGENT_ID': '$AGENT_ID',
    'DIAGNOSER_AGENT_NAME': '$AGENT_NAME',
    'DIAGNOSER_AGENT_VERSION': '$AGENT_VERSION'
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
"

success ".env file updated with your Azure settings."

# ─── STEP 5: Python Environment Setup ─────────────────────────────────────────
header "Step 5: Python Virtual Environment"

read -p "Would you like to initialize/update the virtual environment (.venv)? (y/n): " SETUP_VENV
if [[ $SETUP_VENV =~ ^[Yy]$ ]]; then
    if [ ! -d ".venv" ]; then
        info "Creating virtual environment (.venv)..."
        $PYTHON_CMD -m venv .venv
    fi

    # Activate virtual environment
    info "Activating environment and installing dependencies..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi

    pip install --upgrade pip
    pip install -r requirements.txt
    success "Dependencies installed successfully."
fi

# ─── STEP 6: Run Azure AI Connection Check ────────────────────────────────────
header "Step 6: Azure AI Connection Verification"

read -p "Would you like to run a connection sanity check to verify your RBAC access? (y/n): " RUN_CHECK
if [[ $RUN_CHECK =~ ^[Yy]$ ]]; then
    info "Running verification script..."
    
    # Create a temporary test script
    cat << 'EOF' > scratch/temp_azure_check.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load env
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

if not endpoint:
    print("[ERROR] AZURE_PROJECT_ENDPOINT is not set in .env")
    sys.exit(1)

print(f"Connecting to endpoint: {endpoint}")
print(f"Using deployment: {deployment}")
print("Attempting authentication via DefaultAzureCredential...")

try:
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=endpoint,
        credential=credential
    )
    
    # Simple check: Try to list tools or fetch openai client
    print("DefaultAzureCredential authenticated successfully!")
    print("Retrieving OpenAI client connection...")
    openai_client = client.get_openai_client()
    print("Success! Connection established.")
    print("==== AUTH_OK ====")
    
except Exception as e:
    print(f"\n[ERROR] Authentication or connection failed: {e}")
    print("\nPlease verify that:")
    print("  1. You ran 'az login' with the correct account.")
    print("  2. Your account has the 'Azure AI Developer' or 'Contributor' role on the project resource group.")
    print("  3. The AZURE_PROJECT_ENDPOINT in your .env is correct.")
    sys.exit(1)
EOF

    # Run the check
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        .venv/Scripts/python.exe scratch/temp_azure_check.py
    else
        .venv/bin/python scratch/temp_azure_check.py
    fi
    
    # Clean up
    rm scratch/temp_azure_check.py
else
    info "Sanity check skipped. Setup is complete!"
fi

header "Setup Complete! You are ready to build."
info "To start the system:"
echo -e "  1. Start the target mock server:  ${CYAN}uvicorn simulator.mock_server:app --port 8090${NC}"
echo -e "  2. Start the recovery pipeline:   ${CYAN}python main.py${NC}"
echo -e "  3. Inject a failure:              ${CYAN}python -m simulator.failure_injector db_crash${NC}"
echo ""
