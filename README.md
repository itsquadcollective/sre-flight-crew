# Self-Healing SRE Flight Crew
### Autonomous Multi-Agent Server Recovery System

> An AI-powered system that detects server failures, reasons through root causes using Azure AI Foundry, and remediates incidents in under 60 seconds.

**Microsoft Hackathon 2026**
**Track:** Reasoning Agents

---

## Proof of Concept
This project is a **Proof of Concept (PoC)** demonstrating high-fidelity autonomous SRE reasoning agents. While not a production-grade MVP, it provides a transparent end-to-end reasoning pipeline for infrastructure recovery workflows.

---

## The Problem

Server downtime is expensive and constant. A single outage costs businesses **$5,600 per minute** in lost revenue. Today's incident response is entirely manual: an on-call engineer wakes at 3 AM, SSH's into the server, manually reads messy log files, cross-references documentation, and executes recovery scripts. This process takes **15–45 minutes** on average. For startups and small teams without 24/7 on-call coverage, sites stay down for hours.

Existing monitoring tools (Datadog, PagerDuty, CloudWatch) detect incidents and **alert humans**. They do not fix anything.

## Solution

The **Self-Healing SRE Flight Crew** is an autonomous 4-agent system built with **Python** and **Azure AI Foundry**. It detects, diagnoses, and remediates failures without human input, providing a transparent audit trail of its reasoning.

## Pipeline

Each agent is a specialized reasoner in an async event-driven pipeline:

### 1. WATCHMAN (Detection)
- Scans `logs/server.log` for error patterns.
- Classifies severity and classifies error types.

### 2. DIAGNOSER (Root-Cause Analysis)
- Performs multi-step reasoning via **Azure AI Foundry**.
- Matches signals against known runbooks or reasons from first principles.

### 3. FIXER (Remediation)
- Executes recovery scripts (e.g., restarting databases, clearing caches).
- Verifies system health post-recovery.

### 4. CHRONICLER (Memory)
- Persists incident data to `data/pattern_memory.json` for future analysis.

---

## Architecture

```
┌──────────────────────────────────────┐
│       SIMULATED TARGET SERVER        │
└──────────────────┬───────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
   ┌───────────┐       ┌───────────┐
   │ WATCHMAN  │ ────► │ DIAGNOSER │ ◄── Azure AI Foundry
   └───────────┘       └─────┬─────┘
         ▲                   │
         │             ┌─────▼─────┐
         │             │   FIXER   │
         └─────────────┴─────┬─────┘
                             │
                       ┌─────▼─────┐
                       │CHRONICLER │
                       └───────────┘
```

---

## Project Structure

```bash
sre-flight-crew/
├── agents/        # Autonomous reasoning agents
├── dashboard/     # Status interface
├── docs/          # Technical documentation
├── shared/        # Shared schemas and config
├── simulator/     # Failure injection tools
├── tests/         # Automation test suite
└── main.py        # System orchestrator
```

## Quick Start

### Prerequisites
- Python 3.11+
- Azure account with AI Foundry project
- `az` CLI

### Installation

```bash
# 1. Clone & Setup
git clone https://github.com/[YOUR-ORG]/sre-flight-crew.git
cd sre-flight-crew
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows

# 2. Dependencies & Env
pip install -r requirements.txt
cp .env.example .env
az login
```

### Execution

```bash
# Start Simulated Server
python -m uvicorn simulator.mock_server:app --port 8090

# Start Pipeline
python main.py

# Inject Failure
python -m simulator.failure_injector db_crash
```

---

## Testing & Evaluation

```bash
# Run All Tests
pytest -v
```

Refer to [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) for detailed scenarios.

---

## License
Licensed under the **Apache License 2.0**. Open source contributions are welcome.

---

## Contact
Suggestions or contributions: [pordan.ethan@gmail.com](mailto:pordan.ethan@gmail.com)

---

**Built for Microsoft Hackathon 2026**
