# System Architecture Document (SAD)
## Project: Self-Healing SRE Flight Crew
### Autonomous Multi-Agent Server Recovery System

**Version:** 1.0 | **Date:** June 10, 2026 | **Hackathon:** Agents League – AI Skills Fest 2026 | **Track:** Reasoning Agents

---

## 1. Document Control

| Field | Detail |
|---|---|
| Project Name | Self-Healing SRE Flight Crew |
| Document Type | System Architecture Document (SAD) |
| Version | 1.0 |
| Date | June 10, 2026 |
| Lead Architect | Giant |
| Track | Reasoning Agents |
| Submission Deadline | June 14, 2026 – 11:59 PM PT |

---

## 2. System Overview

### 2.1 Problem Statement

Server downtime costs businesses an estimated **$5,600 per minute** in lost revenue. Current incident response is entirely human-dependent: an engineer wakes at 3 AM, manually reads messy log files, cross-references runbooks, then executes recovery scripts. This process takes 15–45 minutes on average. Small and mid-size businesses often have no on-call engineer at all.

### 2.2 Solution Summary

The **Self-Healing SRE Flight Crew** is a 4-agent autonomous backend system built on **Python** and **Azure AI Foundry** that detects, diagnoses, and remediates server failures in under 60 seconds — with zero human intervention. Every diagnosis produces a transparent, auditable **reasoning trace** powered by an Azure AI o-series model, making the system's decisions explainable and verifiable.

### 2.3 Core Design Principles

| Principle | Meaning |
|---|---|
| **Visible Reasoning** | Every diagnosis produces a human-readable chain-of-thought. The system never acts silently. |
| **Chain Custody** | Each agent receives a typed structured object from the previous agent. Nothing is hardcoded between steps. |
| **Simulation-Safe** | All components run against a fully simulated server. No real production infrastructure required. |
| **Evaluation-First** | The system ships with a built-in evaluation harness — 10 test scenarios, measurable accuracy. |
| **Demo-Driven Design** | If it doesn't show on the dashboard or improve the reasoning trace, it is low priority for this sprint. |

---

## 3. Architecture Overview

### 3.1 Environment Layers

The system operates across three distinct layers:

```
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 1: AZURE AI FOUNDRY  (Cloud)                                  ║
║                                                                      ║
║  ● Model Deployment: gpt-4.1 (reasoning)                              ║
║  ● SDK: azure-ai-projects (AIProjectClient)                          ║
║  ● Auth: DefaultAzureCredential (az login via student subscription)  ║
║  ● Feature: Thinking / reasoning token extraction                    ║
╚══════════════════════════════════════════════════════════════════════╝
                              ▲  HTTPS API calls
                              │
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 2: PYTHON AGENT RUNNER  (Local Machine / Dev VM)              ║
║                                                                      ║
║  ● main.py  — Orchestrator                                           ║
║  ● agents/watchman.py     — Agent 1: Detection                       ║
║  ● agents/diagnoser.py    — Agent 2: Reasoning (calls Foundry)       ║
║  ● agents/fixer.py        — Agent 3: Remediation                     ║
║  ● agents/chronicler.py   — Agent 4: Memory                          ║
║  ● api/dashboard_api.py   — Serves data to Frontend                  ║
╚══════════════════════════════════════════════════════════════════════╝
          ▲  reads/writes files        ▲  executes scripts
          │                            │
╔══════════════════════════════════════════════════════════════════════╗
║  LAYER 3: SIMULATED SERVER ENVIRONMENT  (Local)                      ║
║                                                                      ║
║  ● target_server/server.py  — FastAPI app (crashes on demand)        ║
║  ● target_server/server.log — Live log output                        ║
║  ● knowledge_base/runbook.md — SRE runbook (RAG knowledge source)    ║
║  ● scripts/                 — Bash remediation scripts               ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 3.2 Full Data Flow

```
[FastAPI Target Server]
        │ generates errors on demand
        ▼
[server.log]  ◄──── WATCHMAN polls every 5 seconds
        │                    │
        │         detects "ERROR 500" or "DB_LOCK"
        │                    │
        │                    ▼
        │           IncidentEvent {
        │             incident_id, timestamp,
        │             error_type, log_context (last 20 lines),
        │             severity
        │           }
        │                    │
        │                    ▼
        │           DIAGNOSER
        │           reads runbook.md + IncidentEvent
        │           ──────────────────────────────────►  Azure AI Foundry
        │                                                  o-series model
        │                                                  returns thinking_trace
        │           ◄──────────────────────────────────
        │           DiagnosisResult {
        │             thinking_trace, root_cause,
        │             confidence, recommended_action,
        │             severity, reasoning_steps[]
        │           }
        │                    │
        │                    ▼
        │           FIXER
        │           selects script from ACTION_MAP
        │           executes: e.g. restart_service.sh postgres
        │           polls /health endpoint
        │           RemediationResult {
        │             action_taken, recovery_confirmed,
        │             duration_seconds, status_after
        │           }
        │                    │
        │                    ▼
        │           CHRONICLER
        │           writes to pattern_memory.json
        │           updates pattern_summary
        │                    │
        │                    ▼
        │           DASHBOARD API  ──────►  Frontend Dashboard
        │                                   🔴/🟠/🟢 Status
        │                                   Live Reasoning Trace
        │                                   Incident History Table
```

---

## 4. Component Specifications

### 4.1 Agent 1 — WATCHMAN

| Field | Detail |
|---|---|
| **File** | `agents/watchman.py` |
| **Role** | Continuous log monitor and incident detector |
| **Trigger** | Automatic — runs on a 5-second polling loop |
| **Input** | Path to `server.log` |
| **Output** | `IncidentEvent` object |
| **Azure AI Used** | ❌ None — pure Python file I/O |
| **Calls** | Diagnoser (passes IncidentEvent) |

**Core Logic (Pseudocode):**
```python
def watch_log(log_path: str):
    last_position = 0
    while True:
        with open(log_path, 'r') as f:
            f.seek(last_position)
            new_lines = f.readlines()
            last_position = f.tell()
        
        for line in new_lines:
            if any(pattern in line for pattern in ERROR_PATTERNS):
                context = get_last_n_lines(log_path, n=20)
                incident = IncidentEvent(
                    incident_id=str(uuid4()),
                    timestamp=datetime.utcnow().isoformat(),
                    error_type=classify_error(line),
                    raw_log_line=line,
                    log_context=context,
                    severity=assess_severity(line)
                )
                trigger_pipeline(incident)
        
        time.sleep(5)
```

**ERROR_PATTERNS to detect:**
- `"ERROR 500"`
- `"HTTP 500"`
- `"DB_LOCK"`
- `"CRITICAL"`
- `"Connection refused"`
- `"OOM"` (out of memory)

**Output Schema:**
```json
{
  "incident_id": "uuid-v4",
  "timestamp": "2026-06-10T03:14:22Z",
  "error_type": "HTTP_500 | DB_LOCK | TIMEOUT | MEMORY_OVERFLOW | CRASH",
  "raw_log_line": "[CRITICAL] HTTP 500 - Internal Server Error",
  "log_context": ["...last 20 lines of log..."],
  "severity": "LOW | MEDIUM | HIGH | CRITICAL"
}
```

---

### 4.2 Agent 2 — DIAGNOSER ⭐ (Primary Reasoning Agent)

| Field | Detail |
|---|---|
| **File** | `agents/diagnoser.py` |
| **Role** | Root cause analysis via multi-step AI reasoning |
| **Trigger** | Called by Watchman with IncidentEvent |
| **Input** | `IncidentEvent` + contents of `runbook.md` |
| **Output** | `DiagnosisResult` object with full reasoning trace |
| **Azure AI Used** | ✅ YES — o-series model via Azure AI Foundry |
| **Calls** | Fixer (passes DiagnosisResult) |

**This is the winning component. It must produce visible, step-by-step reasoning.**

**Azure AI Foundry Call:**
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os, json

client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_ENDPOINT"],
    credential=DefaultAzureCredential()
)

def analyze(incident: IncidentEvent) -> DiagnosisResult:
    runbook_content = open("knowledge_base/runbook.md").read()
    
    response = client.inference.get_chat_completions(
        model_deployment_name=os.environ["MODEL_DEPLOYMENT_NAME"],
        messages=[
            {"role": "system", "content": DIAGNOSER_SYSTEM_PROMPT},
            {"role": "user", "content": f"""
INCIDENT DETECTED:
Timestamp: {incident.timestamp}
Error Type: {incident.error_type}
Severity: {incident.severity}

LOG CONTEXT (last 20 lines):
{chr(10).join(incident.log_context)}

SRE RUNBOOK:
{runbook_content}

Analyze this incident step by step. Return valid JSON only.
            """}
        ],
        response_format={"type": "json_object"},
        max_tokens=2000
    )
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    return DiagnosisResult(
        incident_id=incident.incident_id,
        thinking_trace=data["thinking_trace"],
        root_cause=data["root_cause"],
        confidence=data["confidence"],
        recommended_action=data["recommended_action"],
        severity=data["severity"],
        reasoning_steps=data["reasoning_steps"]
    )
```

**Diagnoser System Prompt:**
```
You are an expert Site Reliability Engineer (SRE) AI agent. 
Your job is to analyze server error logs and diagnose root causes.

REASONING PROCESS — follow these steps in order:
1. Scan the log context for the primary error signature
2. Identify any secondary patterns (timing, frequency, related services)
3. Match the pattern against the provided runbook
4. Determine the root cause with a confidence score (0.0 to 1.0)
5. Select the single best remediation action from the runbook
6. Summarize your reasoning in plain English

RULES:
- NEVER recommend an action not in the runbook
- ALWAYS return valid JSON, no markdown, no preamble
- If confidence < 0.6, set recommended_action to "escalate_to_human"
- thinking_trace must be plain English, written as if explaining to a junior engineer

RETURN THIS EXACT JSON STRUCTURE:
{
  "thinking_trace": "Step 1: I examined lines 14-18 and found...",
  "root_cause": "database_lock",
  "confidence": 0.94,
  "recommended_action": "restart_postgres",
  "severity": "HIGH",
  "reasoning_steps": ["Identified error pattern", "Cross-referenced runbook", "Selected action"]
}
```

**Output Schema:**
```json
{
  "incident_id": "uuid (from Watchman)",
  "thinking_trace": "Step 1: Examined log context. Lines 16-20 show repeated DB_LOCK errors originating at 03:14:22Z...\nStep 2: Cross-referenced runbook entry for DB_LOCK...\nStep 3: Pattern matches 'PostgreSQL connection pool exhaustion'...\nStep 4: Recommended action: restart_postgres. Confidence: 94%.",
  "root_cause": "database_lock | memory_overflow | port_conflict | service_crash | cascading_failure",
  "confidence": 0.94,
  "recommended_action": "restart_postgres | restart_nginx | clear_cache | clear_db_lock | restart_app | reboot_service | escalate_to_human",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "reasoning_steps": ["step1 summary", "step2 summary", "step3 summary"]
}
```

---

### 4.3 Agent 3 — FIXER

| Field | Detail |
|---|---|
| **File** | `agents/fixer.py` |
| **Role** | Execute remediation and confirm recovery |
| **Trigger** | Called by Diagnoser with DiagnosisResult |
| **Input** | `DiagnosisResult` (specifically `recommended_action`) |
| **Output** | `RemediationResult` object |
| **Azure AI Used** | ❌ None — deterministic script execution |
| **Calls** | Chronicler (passes RemediationResult) |

**Action Map:**
```python
ACTION_MAP = {
    "restart_postgres":  ["bash", "./scripts/restart_service.sh", "postgres"],
    "restart_nginx":     ["bash", "./scripts/restart_service.sh", "nginx"],
    "restart_app":       ["bash", "./scripts/restart_service.sh", "app"],
    "clear_db_lock":     ["bash", "./scripts/clear_db_lock.sh"],
    "clear_cache":       ["bash", "./scripts/clear_cache.sh"],
    "reboot_service":    ["bash", "./scripts/restart_service.sh", "all"],
    "escalate_to_human": None  # triggers dashboard alert only
}
```

**Recovery Confirmation:**
```python
def confirm_recovery(health_url: str, max_retries=10, interval_sec=3) -> bool:
    for attempt in range(max_retries):
        try:
            r = requests.get(health_url, timeout=2)
            if r.status_code == 200 and r.json().get("status") == "online":
                return True
        except Exception:
            pass
        time.sleep(interval_sec)
    return False
```

**Output Schema:**
```json
{
  "incident_id": "uuid",
  "action_taken": "restart_postgres",
  "script_executed": "./scripts/restart_service.sh postgres",
  "execution_stdout": "PostgreSQL service restarted successfully",
  "recovery_confirmed": true,
  "recovery_duration_seconds": 12,
  "server_status_after": "ONLINE",
  "timestamp_resolved": "2026-06-10T03:14:34Z"
}
```

---

### 4.4 Agent 4 — CHRONICLER

| Field | Detail |
|---|---|
| **File** | `agents/chronicler.py` |
| **Role** | Log incident, update pattern memory, feed dashboard |
| **Trigger** | Called by Fixer with all three prior result objects |
| **Input** | `IncidentEvent` + `DiagnosisResult` + `RemediationResult` |
| **Output** | Entry appended to `data/pattern_memory.json` |
| **Azure AI Used** | ❌ None — pure Python JSON I/O |
| **Calls** | Dashboard API reads from its output file |

**pattern_memory.json Structure:**
```json
{
  "incidents": [
    {
      "incident_id": "uuid",
      "timestamp_detected": "2026-06-10T03:14:22Z",
      "timestamp_resolved": "2026-06-10T03:14:34Z",
      "total_duration_seconds": 12,
      "error_type": "DB_LOCK",
      "root_cause": "database_lock",
      "confidence_at_diagnosis": 0.94,
      "action_taken": "restart_postgres",
      "recovery_confirmed": true,
      "thinking_trace": "Step 1: Examined log context..."
    }
  ],
  "pattern_summary": {
    "most_common_cause": "database_lock",
    "avg_recovery_time_seconds": 23,
    "total_incidents": 7,
    "successful_auto_recoveries": 6,
    "success_rate": 0.86,
    "last_updated": "2026-06-10T03:14:34Z"
  }
}
```

---

### 4.5 Simulated Target Server (FastAPI)

| Field | Detail |
|---|---|
| **File** | `target_server/server.py` |
| **Framework** | FastAPI (Python) |
| **Purpose** | Simulates a real web server that can crash on command for demo |

**Endpoints:**

| Endpoint | Method | Behavior |
|---|---|---|
| `/` | GET | Returns 200 OK — server is healthy |
| `/health` | GET | Returns `{"status": "online"}` or `{"status": "offline"}` |
| `/crash/db-lock` | POST | Writes DB_LOCK + HTTP 500 to server.log, marks server unhealthy |
| `/crash/500` | POST | Writes HTTP 500 cascade to server.log |
| `/crash/memory` | POST | Writes OOM/memory overflow to server.log |
| `/recover` | POST | Marks server healthy (called by Fixer script) |

**server.log Format:**
```
2026-06-10T03:14:20Z [INFO]     Request GET / - 200 OK
2026-06-10T03:14:22Z [ERROR]    DB_LOCK: Connection pool exhausted - cannot acquire lock on table 'sessions'
2026-06-10T03:14:22Z [CRITICAL] HTTP 500 - Internal Server Error on /api/data
2026-06-10T03:14:23Z [ERROR]    HTTP 500 - Retry 1/3 failed - /api/users
2026-06-10T03:14:23Z [ERROR]    HTTP 500 - Retry 2/3 failed - /api/users
```

---

### 4.6 Frontend Dashboard

| Field | Detail |
|---|---|
| **Files** | `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` |
| **Tech** | HTML / Vanilla JS / CSS (or React — Frontend Dev's choice) |
| **Data Source** | `api/dashboard_api.py` at `localhost:8001` |
| **Refresh Rate** | Polling every 3 seconds |

**Required Dashboard Panels:**

| Panel | Description |
|---|---|
| **Status Banner** | Full-width indicator: 🔴 SERVER DOWN / 🟠 AGENTS HEALING / 🟢 SERVER LIVE |
| **Agent Activity Rail** | Shows which agent is currently active with a progress indicator |
| **Live Reasoning Trace** | Streams `thinking_trace` text as the Diagnoser produces it |
| **Incident Log Table** | All past incidents from `pattern_memory.json` — columns: time, cause, action, duration |
| **Demo Trigger Button** | Button to fire a crash (calls `/crash/db-lock`) for live demo purposes |
| **Pattern Stats** | Cards showing: total incidents, avg recovery time, success rate |

---

## 5. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| AI Inference | Azure AI Foundry | — | Diagnoser model deployment |
| Model | gpt-4.1 | Latest | Multi-step reasoning + thinking extraction |
| Auth | DefaultAzureCredential | azure-identity | Student subscription auth via `az login` |
| AI SDK | azure-ai-projects | Latest | Azure Foundry API client |
| Backend Language | Python | 3.11+ | All agents + orchestration |
| Target Server | FastAPI + Uvicorn | Latest | Simulated crashable web server |
| Frontend | HTML / JS / CSS | — | Dashboard UI |
| Data Persistence | JSON | — | pattern_memory.json incident log |
| Script Execution | subprocess (Python stdlib) | — | Remediation script runner |
| HTTP | requests | Latest | Health check polling |
| Version Control | Git / GitHub | — | Repository + submission |
| Knowledge Base | Markdown | — | runbook.md as RAG source |

---

## 6. Agent Communication Contracts

All agents communicate via **typed Python dataclasses passed as function arguments**. No message queues, no HTTP between agents — clean, synchronous pipeline.

```python
# main.py — Orchestrator
import asyncio
from agents.watchman import Watchman
from agents.diagnoser import Diagnoser
from agents.fixer import Fixer
from agents.chronicler import Chronicler
from api.dashboard_api import push_update

async def run_pipeline():
    watchman   = Watchman(log_path="target_server/server.log")
    diagnoser  = Diagnoser(runbook_path="knowledge_base/runbook.md")
    fixer      = Fixer(server_health_url="http://localhost:8000/health")
    chronicler = Chronicler(memory_path="data/pattern_memory.json")

    print("[WATCHMAN] Monitoring server log...")
    
    while True:
        incident = await watchman.monitor()           # blocks until incident detected
        
        push_update({"phase": "diagnosing", "incident": incident})
        diagnosis = await diagnoser.analyze(incident)  # calls Azure AI Foundry
        
        push_update({"phase": "fixing", "diagnosis": diagnosis})
        result = await fixer.remediate(diagnosis)      # runs remediation script
        
        push_update({"phase": "logging", "result": result})
        await chronicler.record(incident, diagnosis, result)
        
        push_update({"phase": "recovered", "summary": build_summary(incident, diagnosis, result)})
        
        print(f"[DONE] Incident {incident.incident_id} resolved in {result.recovery_duration_seconds}s")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
```

---

## 7. Evaluation Framework

The submission includes a built-in evaluation harness to demonstrate measurable accuracy — a key differentiator in the Reasoning Agents track.

**10 Test Scenarios:**

| # | Crash Type | Expected Root Cause | Expected Action |
|---|---|---|---|
| 1 | DB connection pool exhausted | `database_lock` | `restart_postgres` |
| 2 | Memory usage > 95% | `memory_overflow` | `clear_cache` |
| 3 | Nginx worker process killed | `service_crash` | `restart_nginx` |
| 4 | Port 5432 already in use | `port_conflict` | `restart_postgres` |
| 5 | FastAPI 500 on /api/data | `application_error` | `restart_app` |
| 6 | Cascade: 10+ 500s in 30 seconds | `cascading_failure` | `reboot_service` |
| 7 | DB_LOCK + simultaneous 500s | `database_lock` | `restart_postgres` |
| 8 | Health check timeout (no response) | `timeout` | `restart_nginx` |
| 9 | Memory leak (gradual 500 increase) | `memory_overflow` | `clear_cache` |
| 10 | Full cold crash (all services down) | `full_crash` | `reboot_service` |

**Target Metrics:**

| Metric | Target |
|---|---|
| Root Cause Correct Rate | ≥ 80% (8/10) |
| Correct Action Selection | ≥ 80% (8/10) |
| Average Recovery Time | < 60 seconds |
| False Positive Rate | < 10% |
| Diagnoser Returns Valid JSON | 100% |

**Running the Eval:**
```bash
python eval/run_eval.py
# Output:
# [EVAL] Scenario 1/10: DB_LOCK → PASS (root_cause=database_lock, confidence=0.94)
# [EVAL] Scenario 2/10: MEMORY → PASS (root_cause=memory_overflow, confidence=0.88)
# ...
# [RESULTS] Root Cause Accuracy: 9/10 (90%) | Action Accuracy: 9/10 (90%)
```

---

## 8. Repository File Structure

```
self-healing-sre/
│
├── README.md                       ← Submission README
├── requirements.txt                ← All Python dependencies
├── .env.example                    ← Environment variable template
├── .gitignore
│
├── main.py                         ← Orchestrator entry point
│
├── agents/
│   ├── __init__.py
│   ├── watchman.py                 ← Agent 1: Log monitor
│   ├── diagnoser.py                ← Agent 2: Azure AI reasoning
│   ├── fixer.py                    ← Agent 3: Remediation executor
│   └── chronicler.py               ← Agent 4: Memory logger
│
├── target_server/
│   ├── server.py                   ← FastAPI crashable server
│   ├── log_simulator.py            ← Generates fake crash logs
│   └── server.log                  ← Live log output (gitignored)
│
├── knowledge_base/
│   └── runbook.md                  ← SRE runbook (RAG source, ~10 scenarios)
│
├── scripts/
│   ├── restart_service.sh          ← Restart any named service
│   ├── clear_db_lock.sh            ← Clear database lock
│   └── clear_cache.sh              ← Clear application cache
│
├── data/
│   └── pattern_memory.json         ← Incident log (auto-generated)
│
├── api/
│   └── dashboard_api.py            ← FastAPI serving dashboard data
│
├── frontend/
│   ├── index.html                  ← Dashboard entry
│   ├── app.js                      ← Dashboard polling logic
│   └── styles.css                  ← Dashboard styles
│
├── eval/
│   └── run_eval.py                 ← 10-scenario evaluation harness
│
└── docs/
    ├── SAD.md                      ← This document
    ├── PDR.md                      ← Project Design Review
    └── SUBMISSION_GUIDE.md         ← Submission checklist & guide
```

---

## 9. Environment Variables (.env.example)

```bash
# Azure AI Foundry
AZURE_AI_FOUNDRY_ENDPOINT=https://YOUR-PROJECT.cognitiveservices.azure.com/
MODEL_DEPLOYMENT_NAME=gpt-4.1

# Target Server
TARGET_SERVER_URL=http://localhost:8000
TARGET_LOG_PATH=./target_server/server.log

# Dashboard API
DASHBOARD_API_PORT=8001

# Paths
RUNBOOK_PATH=./knowledge_base/runbook.md
MEMORY_PATH=./data/pattern_memory.json
```

> **Auth Note:** Authentication uses `DefaultAzureCredential`. Run `az login` before starting the system. No API keys stored in code or `.env`.

---

*SAD v1.0 — Self-Healing SRE Flight Crew — Agents League 2026*
