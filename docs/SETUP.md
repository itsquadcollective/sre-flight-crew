# Developer Setup Guide

## Quick Start (Choose Your Platform)

**Windows** · **macOS** · **Linux**

---

## Prerequisites

Before you start, ensure you have:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **Azure CLI** (`az` command-line tool)
- **Azure Account** with Foundry access

---

## Step 1: Clone Repository

```bash
git clone https://github.com/itsquadcollective/sre-flight-crew.git
cd sre-flight-crew
```

---

## Step 2: Install Azure CLI

### Windows

```powershell
# Using winget (recommended)
winget install Microsoft.AzureCLI

# OR using Chocolatey
choco install azure-cli

# Verify installation
az --version
```

### macOS

```bash
# Using Homebrew
brew install azure-cli

# Verify installation
az --version
```

### Linux (Ubuntu/Debian)

```bash
# Add Microsoft repository
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version
```

---

## Step 3: Authenticate with Azure

```bash
# Log in to your Azure account
az login

# Set your active subscription
az account set --subscription <your-subscription-id>

# Verify
az account show
```

**Note:** You'll be prompted to authenticate in your browser. Follow the prompts.

---

## Step 4: Create Python Virtual Environment

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### Windows (Command Prompt)

```cmd
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate.bat
```

### macOS / Linux (Bash)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

**Verify activation:**
```bash
# Your prompt should show (.venv) prefix
# Example: (.venv) user@machine:sre-flight-crew $
```

---

## Step 5: Install Python Dependencies

```bash
# Make sure venv is activated (see Step 4)

pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `fastapi`, `uvicorn` — API framework
- `azure-ai-projects`, `azure-identity` — Foundry SDK
- `pydantic` — Data validation
- `pytest` — Testing framework

---

## Step 6: Configure Environment

```bash
# Copy template to local .env
cp .env.example .env

# Edit .env with your values
# Windows:   notepad .env
# macOS/Linux: nano .env
```

**Required values:**
```bash
AZURE_PROJECT_ENDPOINT=https://your-foundry-project.api.azureml.ms
MODEL_DEPLOYMENT_NAME=gpt-4.1
DIAGNOSER_AGENT_ID=your-agent-id-here
DIAGNOSER_AGENT_NAME=DIAGNOSER
```

**How to find these:**
1. Log in to [Azure AI Foundry](https://foundry.azure.com)
2. Open your project
3. Go to **Project Settings** → copy **Project endpoint**
4. Go to **Models** → find your gpt-4.1 deployment name
5. Go to **Agents** → find your DIAGNOSER agent ID

---

## Step 7: Verify Setup

### Test Python & Dependencies

```bash
# Activate venv first (if not already)
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Test imports
python -c "import azure.ai.projects; print('✓ Azure SDK works')"
python -c "import fastapi; print('✓ FastAPI works')"
```

### Test Azure Connection

```bash
# Check your Azure login
az account show

# Test Foundry connection
python -c "
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
print('✓ Foundry SDK imports successfully')
"
```

---

## Step 8: Run the Pipeline

**Terminal 1: Start mock server**
```bash
python -m uvicorn simulator.mock_server:app --port 8090
# Output: Uvicorn running on http://127.0.0.1:8090
```

**Terminal 2: Start pipeline**
```bash
python main.py
# Output: [DIAGNOSER] Connected to Azure AI Foundry
```

**Terminal 3: Inject failure**
```bash
python -m simulator.failure_injector db_crash
# Watch Terminal 2 for diagnosis and recovery
```

---

## Troubleshooting

### "Python not found"

```bash
# Check if Python is installed
python --version
# If not, install from https://www.python.org/downloads/

# On macOS, you might need python3:
python3 --version
```

### "Azure CLI not found"

Install using one of the methods in Step 2 for your platform.

### "venv activation not working"

**Windows PowerShell:**
```powershell
# Run this first if you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.venv\Scripts\Activate.ps1
```

**macOS/Linux bash:**
```bash
# Make sure you're in the repo directory
source .venv/bin/activate
```

### "requirements.txt installation fails"

```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Then retry
pip install -r requirements.txt
```

### "Foundry authentication fails"

```bash
# Re-authenticate
az login
az account set --subscription <your-subscription-id>

# Verify .env has correct values
cat .env
```

---

## Next Steps

✓ Setup complete!

1. **Run tests**: `pytest -v`
2. **Try the demo**: Follow Step 8 above
3. **Read architecture**: See [SAD.md](SAD.md)
4. **Understand design**: See [PDR.md](PDR.md)

---

## Getting Help

- **Azure CLI issues?** → [Azure CLI docs](https://learn.microsoft.com/en-us/cli/azure/)
- **Foundry setup?** → [Azure AI Foundry docs](https://learn.microsoft.com/en-us/azure/ai-studio/)
- **Python venv?** → [Python venv docs](https://docs.python.org/3/library/venv.html)

---

**Last updated:** June 14, 2026
