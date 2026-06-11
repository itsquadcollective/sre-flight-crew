# SRE Flight Crew — Testing and Verification Guide

This guide describes how to test and verify the autonomous incident response pipeline, demonstrating the prowess of our SRE agents and verifying first-principles reasoning for un-runbooked, real-world failure scenarios.

---

## 1. Core Agent Capabilities (Prowess)

Our architecture utilizes a decoupled event-driven team of four specialized agents:

1. **Watchman (Agent 1 - Detection)**: Tail-scans the FastAPI server log (`logs/server.log`) asynchronously, parsing logs, classifying severities, and debouncing alerts.
2. **Diagnoser (Agent 2 - Reasoning)**: 
   * Powered by the reasoning-capable model (`gpt-4.1`).
   * Connected via the Azure AI Foundry **Responses API** (`openai_client.responses.create`) targeting Version 11 of the `DIAGNOSER` agent connection.
   * Utilizes **`knowledgebase-new`** configured with `minimal` reasoning effort, bypassing regional search query planning errors.
   * Implements a hybrid **local Prompt RAG fallback** where runbooks are read in Python and passed directly in the prompt context to ensure ultra-fast, zero-downtime execution.
3. **Fixer (Agent 3 - Remediation)**: Translates recommended actions into FastAPI recovery API calls and verifies restoration with a health-check polling loop.
4. **Chronicler (Agent 4 - Memory)**: Records resolved incidents to `data/pattern_memory.json` to build institutional memory.

---

## 2. Test Phase 1: Automated Unit Testing

Run the full pytest suite to verify agent logic, parsing regex, mock API routing, and state machines:

```bash
# Windows
.venv\Scripts\python.exe -m pytest

# macOS / Linux
.venv/bin/python -m pytest
```

### What is covered:
* **Log parsing & classification** in `test_watchman.py`.
* **Remediation client routing, success states, and 409 conflict handles** in `test_fixer.py`.
* **API response cleaning, JSON parsing, and schema clamping** in `test_diagnoser.py`.
* **Simulated crash triggers and health responses** in `test_simulator.py`.

---

## 3. Test Phase 2: End-to-End Runbooked Recovery

Test the E2E pipeline with known runbooked failures:

### Step 1: Start the Target Server
In **Terminal 1**, start the simulated e-commerce FastAPI server:
```bash
.venv\Scripts\python.exe -m uvicorn simulator.mock_server:app --port 8090
```

### Step 2: Start the Orchestrator Pipeline
In **Terminal 2**, start the main SRE flight crew orchestrator:
```bash
.venv\Scripts\python.exe main.py
```

### Step 3: Inject a Database Crash (`db_crash`)
In **Terminal 3**, run the chaos injection command:
```bash
.venv\Scripts\python.exe -m simulator.failure_injector db_crash
```
* **Expected Outcome**: The Watchman detects `DB_CRASH`, the Diagnoser matches the log to `runbook_db_crash.md`, prescribes `restart_db`, the Fixer calls the recovery endpoint, and the server returns to `200 OK` in under 1 second.

### Step 4: Inject a Memory Leak (`memory_spike`)
In **Terminal 3**, run the chaos injection command:
```bash
.venv\Scripts\python.exe -m simulator.failure_injector memory_spike
```
* **Expected Outcome**: The Watchman detects `MEMORY_SPIKE`, the Diagnoser matches the log to `runbook_memory_spike.md`, prescribes `clear_cache`, the Fixer flushes the response cache, and the server returns to `200 OK` in under 2 seconds.

---

## 4. Test Phase 3: The Versatility Test (First-Principles Reasoning)

To prove that the pipeline is not just a hardcoded mapping and can handle **novel real-world failures**, we test the agent's ability to reason from first principles with **no runbook**.

We have added a new failure mode: **`service_crash`** simulating application worker process death. 

### Step 1: Verify No Runbook Exists
Inspect the `agents/diagnoser/knowledge_base/` folder. Notice that there is no file named `runbook_service_crash.md`. The cloud knowledge base also has no records of it.

### Step 2: Inject the Service Crash
With **Terminal 1 (Mock Server)** and **Terminal 2 (Pipeline)** running, execute in **Terminal 3**:
```bash
.venv\Scripts\python.exe -m simulator.failure_injector service_crash
```

### Step 3: Observe First-Principles Reasoning
In **Terminal 2 (Pipeline)**, watch the logs:
1. **Watchman** detects the crash logs:
   * `FATAL [api] worker process 9921 exited with code 1`
   * `ERROR [runtime] worker unresponsive: ping timeout > 10000ms`
   * `FATAL [system] SERVICE_CRASH — application server DOWN`
2. **Diagnoser** receives the `SERVICE_CRASH` event. Seeing no matching runbook, it defaults to **SOP-based reasoning** (using `sop_general.md` provided in prompt context).
3. The model scans `sop_general.md`, matches the signatures to the **Application Runtime** section:
   > *"Failure mode (service crash): Unhandled exceptions or worker death. The service stops responding entirely. Recovery: `restart_service` — restarts the application process."*
4. It maps the fix to the allowed action schema and outputs:
   ```json
   {
     "root_cause": "service_crash",
     "confidence": 0.97,
     "recovery_action": "restart_service",
     "runbook_reference": "sop_general.md — Section: Application Runtime"
   }
   ```
5. **Fixer** executes `restart_service` via POST to `/sim/recover/restart_service`.
6. **Verification** checks return `200 OK` and the server is restored!

---

## 5. Verification of Institutional Memory

Open `data/pattern_memory.json` to verify that all incident records (including thinking summaries and resolution metrics) are appended correctly:

```json
{
  "incidents": [
    {
      "event_id": "evt_20260611_141223_001",
      "error_type": "DB_CRASH",
      "root_cause": "database_lock",
      "recovery_action": "restart_db",
      "confidence": 0.97,
      "success": true,
      "reasoning_summary": "Step 1: I examined the log context and found the primary error signature..."
    }
  ],
  "total_resolved": 3,
  "last_updated": "2026-06-11T14:12:38.123456Z"
}
```
This serves as our "institutional memory", helping the team review past incidents and enabling the Diagnoser to recognize repeating patterns.
