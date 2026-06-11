#!/usr/bin/env bash
set -euo pipefail

# setup_and_test.sh — automated setup + Azure connection sanity check
# Usage: bash setup_and_test.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Find python
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=python
else
  echo "[ERROR] Python 3 is required but not found. Install Python 3.10+." >&2
  exit 1
fi

# Check git
if ! command -v git >/dev/null 2>&1; then
  echo "[ERROR] Git is required but not found. Install Git and re-run." >&2
  exit 1
fi

# Check az
if ! command -v az >/dev/null 2>&1; then
  echo "[ERROR] Azure CLI (az) not found. Please install and run 'az login' first." >&2
  echo "See: https://learn.microsoft.com/cli/azure/install-azure-cli" >&2
  exit 1
fi

echo "[INFO] Using Python: $($PYTHON_CMD --version 2>&1)"

echo "\n--- .env setup ---"
ENV_FILE=.env
if [ ! -f "$ENV_FILE" ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "[INFO] Created .env from .env.example"
  else
    touch .env
    echo "[INFO] Created empty .env"
  fi
fi

read -r -p "Azure AI Project Endpoint [Default: https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam]: " PROJECT_ENDPOINT
PROJECT_ENDPOINT=${PROJECT_ENDPOINT:-https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam}

read -r -p "Resource Group Name [Default: rg-ochuko]: " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-rg-ochuko}

read -r -p "Model Deployment Name [Default: gpt-4.1]: " MODEL_NAME
MODEL_NAME=${MODEL_NAME:-gpt-4.1}

read -r -p "Diagnoser Agent ID (optional) [Default: none]: " AGENT_ID
AGENT_ID=${AGENT_ID:-none}

read -r -p "Diagnoser Agent Name [Default: DIAGNOSER]: " AGENT_NAME
AGENT_NAME=${AGENT_NAME:-DIAGNOSER}

read -r -p "Diagnoser Agent Version [Default: 11]: " AGENT_VERSION
AGENT_VERSION=${AGENT_VERSION:-11}

# Get current subscription id (if logged in)
SUB_ID=""
if az account show >/dev/null 2>&1; then
  SUB_ID=$(az account show --query id -o tsv | tr -d '\r')
fi

# Write/update .env using a short Python helper for cross-platform correctness
$PYTHON_CMD - <<PY
import os
p='.'
env_path=os.path.join(p,'.env')
updates={
  'AZURE_PROJECT_ENDPOINT':'%s',
  'AZURE_SUBSCRIPTION_ID':'%s',
  'AZURE_RESOURCE_GROUP':'%s',
  'MODEL_DEPLOYMENT_NAME':'%s',
  'DIAGNOSER_AGENT_ID':'%s',
  'DIAGNOSER_AGENT_NAME':'%s',
  'DIAGNOSER_AGENT_VERSION':'%s'
}
updates={k:v for k,v in updates.items() if v}
lines=[]
if os.path.exists(env_path):
    with open(env_path,'r',encoding='utf-8') as f:
        lines=f.readlines()
new_lines=[]
keys_found=set()
for line in lines:
    stripped=line.strip()
    if stripped and not stripped.startswith('#') and '=' in line:
        k,v=line.split('=',1)
        k=k.strip()
        if k in updates:
            new_lines.append(f"{k}={updates[k]}\n")
            keys_found.add(k)
            continue
    new_lines.append(line)
for k,v in updates.items():
    if k not in keys_found:
        new_lines.append(f"{k}={v}\n")
with open(env_path,'w',encoding='utf-8') as f:
    f.writelines(new_lines)
print('Updated .env')
PY
