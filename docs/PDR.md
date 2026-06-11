# Project Design Review (PDR)
## Project: Self-Healing SRE Flight Crew
### Autonomous Multi-Agent Server Recovery System

**Version:** 1.0 | **Date:** June 10, 2026 | **Hackathon:** Agents League – AI Skills Fest 2026 | **Track:** Reasoning Agents

---

## 1. Document Control

| Field | Detail |
|---|---|
| Document Type | Project Design Review (PDR) |
| Version | 1.0 |
| Date | June 10, 2026 |
| Project Director | Giant (Lead Architect) |
| Status | Active – Sprint Begins Today |
| Submission Deadline | June 14, 2026 – 11:59 PM PT |

---

## 2. Problem Statement

### 2.1 Business Problem
Server downtime is a silent, constant, and expensive emergency. The companies that suffer most are not large enterprises with 24/7 NOC teams — they are startups, SMBs, and growing platforms that cannot afford on-call engineers. When their servers crash at 3 AM, nobody wakes up. The site stays down for hours.

Even for teams with on-call engineers, the manual process is slow: wake up, SSH in, scroll through logs, cross-reference documentation, execute recovery commands. Average time-to-recovery: 15–45 minutes. Average cost: thousands of dollars per minute in lost revenue and user trust.

### 2.2 Technical Problem
Existing monitoring tools (Datadog, PagerDuty, AWS CloudWatch) detect incidents and **alert humans**. They do not fix anything. The market gap is: an intelligent system that goes from detection to remediation autonomously, while producing a clear audit trail of its reasoning.

### 2.3 Why AI Solves This
Fixing a server crash is not just automation — it requires judgment. Different error patterns (DB lock vs. memory overflow vs. port conflict) require different actions. A rule-based system needs dozens of hardcoded conditions. An AI reasoning agent can generalize across patterns, cross-reference documentation dynamically, and explain its decisions in plain language.

---

## 3. Design Philosophy

Every design decision in this project is governed by three principles:

**1. Reasoning Over Automation**
Any script can restart a server. What makes this an AI system — and what wins the Reasoning Agents track — is that the Diagnoser shows its work. Every diagnosis produces a step-by-step thinking trace. Judges must be able to read the chain-of-thought and understand exactly why the system took the action it did.

**2. Demo-Driven Design**
We have 4 days. Every engineering decision must serve the demo video. Ask: "Does this show up on the dashboard?" and "Does this improve the judge's ability to see reasoning?" If the answer to both is no, it goes in a future backlog.

**3. Buildable Before Beautiful**
Working pipeline first. Polish second. The order is: Watchman working → Diagnoser reasoning → Fixer remediating → Dashboard showing it. Styling, extra crash scenarios, and optimizations are Day 3 and Day 4 work only.

---

## 4. Key Design Decisions

### Decision 1: No heavy agent framework for MVP
**Options considered:** AutoGen, Semantic Kernel, LangChain, raw Python  
**Decision:** Raw Python orchestration in `main.py`  
**Rationale:** Given a 4-day timeline, adding an agent framework introduces a learning curve, debugging overhead, and abstraction layers that obscure the reasoning chain. The 4-agent pipeline is sequential — Watchman → Diagnoser → Fixer → Chronicler — which maps cleanly to a Python async function chain. Judges see clean, readable code. No "magic" hiding the architecture.  
**Revisit:** Post-hackathon, migrate to Semantic Kernel or AutoGen for production.

### Decision 2: Simulated server environment
**Options considered:** Real cloud VM, Docker container, local FastAPI  
**Decision:** Local FastAPI server with crash-trigger endpoints  
**Rationale:** Demos reliably every time. No cloud costs. No SSH edge cases. The demo video shows a crash triggered by a button click and a recovery in under 60 seconds — the simulation is the feature, not a limitation.

### Decision 3: JSON file for pattern memory (not a database)
**Options considered:** Supabase, SQLite, Redis, flat JSON  
**Decision:** `data/pattern_memory.json`  
**Rationale:** No setup time, no connection strings, readable directly by judges in the GitHub repo, serves the dashboard API trivially. Upgrade path to a real database is documented but not built.

### Decision 4: gpt-4.1 model for Diagnoser
**Options considered:** opus 4.6, sonnet 4.6 gpt 5.4, gpt 4.1 
**Decision:** gpt-4.1
**Rationale:** The reasoning track explicitly rewards multi-step thinking. gpt-4.1 provides strong reasoning capabilities with good token efficiency. The system prompt forces step-by-step output with structured JSON.

### Decision 5: Diagnoser system prompt enforces JSON-only output
**Rationale:** At 3 AM, the Fixer receives the Diagnoser's output and executes a script. A parsing error at that point breaks the pipeline. The Diagnoser system prompt strictly enforces `response_format: json_object` at the API level, plus explicit instructions never to return markdown or preamble. Fail-safes in `diagnoser.py` catch malformed JSON and escalate to human.

---

## 5. Team Structure & Roles

### 5.1 Cell Overview

```
┌─────────────────────────────────────────────────────┐
│        CELL 1: CORE ENGINEERING (6 people)           │
│                                                      │
│  Giant — Lead Architect + Project Director           │
│  Lead Cloud Architect & DevOps                       │
│  AI Agent Dev 1 (Watchman + Diagnoser)               │
│  AI Agent Dev 2 (Fixer)                              │
│  AI Agent Dev 3 (Orchestration + Chronicler)         │
│  Frontend / UI Developer                             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│     CELL 2: INTEGRATION & TECHNICAL WRITING (2)      │
│                                                      │
│  Foundry IQ Context Manager (Data + Prompts)         │
│  Technical Writer & QA Tester                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│      CELL 3: PITCH & SUBMISSION STRATEGY (2)         │
│                                                      │
│  Creative Director (Brand + Story + Script)          │
│  Project Director (Giant — also Lead Architect)      │
└─────────────────────────────────────────────────────┘
```

### 5.2 Role Definitions

---

#### GIANT — Lead Architect & Project Director
**Primary responsibility:** Azure AI Foundry integration, Diagnoser agent (thinking extraction), overall architecture validation, team coordination, and final submission oversight.

**Owns:**
- Azure AI Foundry project + model deployment
- `agents/diagnoser.py` (the critical reasoning agent)
- All Azure SDK calls (`azure-ai-projects`, `DefaultAzureCredential`)
- Diagnoser thinking extraction pipeline
- Evaluation harness design
- Architecture documentation (SAD)
- Evening team syncs (30 min each evening)
- Final submission package review

**Does NOT own:** Frontend code, bash scripts, README writing, pitch slides

---

#### LEAD CLOUD ARCHITECT & DEVOPS
**Primary responsibility:** Development environment, GitHub repository management, and the simulated target server (the thing that crashes).

**Owns:**
- GitHub repository setup, branching strategy, merge coordination
- `requirements.txt`, `.env.example`, `.gitignore`
- `target_server/server.py` — FastAPI crashable server
- `target_server/log_simulator.py` — generates fake crash logs
- All crash endpoints (`/crash/db-lock`, `/crash/500`, `/crash/memory`)
- Bash remediation scripts (`scripts/restart_service.sh`, etc.)
- Ensuring everyone can `git clone` and run `python main.py` in under 10 minutes

---

#### AI AGENT DEV 1 — Watchman + Diagnoser Integration
**Primary responsibility:** `agents/watchman.py` and integrating the Diagnoser with the Watchman output.

**Owns:**
- `agents/watchman.py` — complete polling loop
- `IncidentEvent` dataclass definition
- Watchman error pattern matching (all 6 error signatures)
- Watchman → Diagnoser handoff (testing the IncidentEvent passes correctly)
- Watchman unit tests

---

#### AI AGENT DEV 2 — Fixer
**Primary responsibility:** `agents/fixer.py` and the recovery confirmation loop.

**Owns:**
- `agents/fixer.py` — complete ACTION_MAP + execution logic
- `RemediationResult` dataclass
- Recovery confirmation polling loop (hits `/health` endpoint)
- Fixer unit tests (verify each action in ACTION_MAP triggers correctly)
- Coordinating with Cloud Architect on script naming consistency

---

#### AI AGENT DEV 3 — Orchestration + Chronicler
**Primary responsibility:** `main.py` orchestrator and `agents/chronicler.py`.

**Owns:**
- `main.py` — the pipeline that wires all 4 agents together
- `agents/chronicler.py` — writes to `pattern_memory.json`
- `data/pattern_memory.json` schema and initialization
- Error handling in the pipeline (what happens if an agent fails)
- `api/dashboard_api.py` — FastAPI endpoint that serves `pattern_memory.json` to frontend

---

#### FRONTEND / UI DEVELOPER
**Primary responsibility:** The dashboard that makes everything visible to judges.

**Owns:**
- `frontend/index.html` — all dashboard HTML
- `frontend/app.js` — polling logic + dynamic updates
- `frontend/styles.css` — layout and visual styling
- Status banner (🔴/🟠/🟢) with smooth transitions
- Live reasoning trace panel (renders `thinking_trace` character by character)
- Incident log table (pulls from dashboard API)
- Demo trigger button (calls `/crash/db-lock`)
- Pattern stats cards (total incidents, avg time, success rate)

**Constraint:** Dashboard must look good in a screen recording. This is what judges see. Clean, dark theme, clear typography, high contrast.

---

#### FOUNDRY IQ CONTEXT MANAGER — Data & Prompts
**Primary responsibility:** The knowledge base and system prompts that make the Diagnoser reason correctly.

**Owns:**
- `knowledge_base/runbook.md` — the SRE runbook (minimum 10 scenarios)
- Diagnoser system prompt — write, test, iterate
- Prompt stress testing (does the Diagnoser hallucinate? does it return valid JSON?)
- Log message corpus — write realistic fake log lines for all 10 eval scenarios
- Works directly with Giant on prompt refinement

**Runbook.md must cover:**
1. PostgreSQL DB lock / connection pool exhaustion
2. Memory overflow (OOM killer)
3. Nginx worker crash
4. Port conflict (service already running)
5. Application-level 500 (FastAPI crash)
6. Cascading failures (multiple services)
7. DB lock + simultaneous HTTP 500
8. Health check timeout
9. Memory leak pattern
10. Full service crash (all down)

---

#### TECHNICAL WRITER & QA TESTER
**Primary responsibility:** End-to-end testing, README.md, and the submission package.

**Owns:**
- `README.md` — the submission README (use template from SUBMISSION_GUIDE.md)
- `eval/run_eval.py` — the 10-scenario evaluation harness
- Bug tracking (GitHub Issues) — log every broken pipeline step
- End-to-end QA: trigger crash → verify Watchman fires → verify Diagnoser returns valid JSON → verify Fixer runs → verify Dashboard updates
- Submission checklist verification (from SUBMISSION_GUIDE.md)

---

#### CREATIVE DIRECTOR — Brand + Story + Script
**Primary responsibility:** Project identity, pitch slides, and demo video script.

**Owns:**
- Project name (confirm or improve "Self-Healing SRE Flight Crew")
- Logo design (simple, vector, dark-theme compatible)
- Color palette (3 colors — must work with dashboard theme)
- Pitch slide deck (8–10 slides — see SUBMISSION_GUIDE.md for required slides)
- Word-for-word 5-minute demo script (narrated by Project Director)
- Demo video editing and upload

---

## 6. Sprint Roadmap — Explicit Daily Task Assignments

> **Legend:** ✅ = Definition of Done | ⚡ = Critical path item | 🤝 = Requires coordination

---

### DAY 0 — June 10, 2026 (TODAY)
**Sprint Goal:** Foundation is set. Every team member has a working dev environment, the GitHub repo is live, Watchman is polling a log file, and Azure Foundry is authenticated.

---

#### GIANT — Lead Architect
| # | Task | Notes |
|---|---|---|
| 1 | Create Azure AI Foundry project in student subscription | Go to ai.azure.com → create project |
| 2 | Deploy a gpt-4.1 model | Note down the deployment name exactly |
| 3 | Run `az login` and test `DefaultAzureCredential` auth | Use the quick-test script below |
| 4 | Make one successful API call from Python | Confirm response object structure |
| 5 | Share `AZURE_AI_FOUNDRY_ENDPOINT` + `MODEL_DEPLOYMENT_NAME` with Context Manager | DM in team chat — never commit to GitHub |
| 6 | Create GitHub repository: `self-healing-sre` | Add all members as collaborators |
| 7 | Commit folder skeleton (all empty dirs + `.gitignore`) | Cloud Architect handles requirements.txt |
| 8 | Run evening sync (30 min) | Verify everyone completed their Day 0 DoD |

**✅ DoD:** One successful Azure AI Foundry API call from Python. GitHub repo accessible to all members.

**Quick auth test:**
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os

client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_ENDPOINT"],
    credential=DefaultAzureCredential()
)
response = client.inference.get_chat_completions(
    model_deployment_name=os.environ["MODEL_DEPLOYMENT_NAME"],
    messages=[{"role": "user", "content": "Say: AUTH_OK"}],
    max_tokens=10
)
print(response.choices[0].message.content)  # Should print AUTH_OK
```

---

#### LEAD CLOUD ARCHITECT & DEVOPS
| # | Task | Notes |
|---|---|---|
| 1 | Clone repo, set up `requirements.txt` with all needed packages | `fastapi`, `uvicorn`, `azure-ai-projects`, `azure-identity`, `requests` |
| 2 | Create full folder structure (match SAD §8 exactly) | Empty `__init__.py` files in all agent dirs |
| 3 | Write `.env.example` | One line per variable, comment each |
| 4 | Write `target_server/log_simulator.py` | Takes number of lines as arg, outputs to `server.log` |
| 5 | Write `target_server/server.py` skeleton | Just `/health` endpoint for now |
| 6 | Test: `python log_simulator.py 50` generates a valid log file | |
| 7 | Push everything to GitHub | |

**✅ DoD:** `python log_simulator.py 50` generates a `server.log` with ERROR 500 and DB_LOCK lines. All teammates can `pip install -r requirements.txt` without errors.

**log_simulator.py minimum output:**
```
2026-06-10T03:14:20Z [INFO] Request GET / - 200 OK
2026-06-10T03:14:21Z [INFO] Request GET /api/data - 200 OK
2026-06-10T03:14:22Z [ERROR] DB_LOCK: Connection pool exhausted
2026-06-10T03:14:22Z [CRITICAL] HTTP 500 - Internal Server Error on /api/data
```

---

#### AI AGENT DEV 1 — Watchman
| # | Task | Notes |
|---|---|---|
| 1 | Read SAD §4.1 fully | Understand IncidentEvent schema |
| 2 | Define `IncidentEvent` as a Python dataclass | In `agents/watchman.py` |
| 3 | Write the polling loop | 5-second interval, reads new lines only |
| 4 | Implement error pattern matching | Match all 6 patterns from SAD §4.1 |
| 5 | Test against log_simulator.py output | Run Watchman against a static log file with known errors |
| 6 | Confirm IncidentEvent object prints correctly | `print(incident.__dict__)` should show all fields |

**✅ DoD:** Running `python agents/watchman.py` against a log file with "ERROR 500" prints a complete IncidentEvent object within 10 seconds of the error appearing.

---

#### AI AGENT DEV 2 — Fixer
| # | Task | Notes |
|---|---|---|
| 1 | Read SAD §4.3 fully | |
| 2 | Define `RemediationResult` as a Python dataclass | |
| 3 | Write placeholder bash scripts (they just `echo` — no real restart needed) | `scripts/restart_service.sh postgres` → "Restarting postgres..." |
| 4 | Write `ACTION_MAP` dict in `agents/fixer.py` | All 6 actions from SAD |
| 5 | Write `execute_action()` function using `subprocess.run()` | |
| 6 | Test: hardcode a `recommended_action="restart_postgres"`, confirm script runs | |

**✅ DoD:** Given a hardcoded `recommended_action`, Fixer executes the correct script and returns a `RemediationResult` object.

---

#### AI AGENT DEV 3 — Orchestration + Chronicler
| # | Task | Notes |
|---|---|---|
| 1 | Read SAD §4.4 and §6 (agent contracts) | |
| 2 | Write `agents/chronicler.py` — reads all three result objects | |
| 3 | Write chronicler logic to append to `pattern_memory.json` | Handle first-run: create file if not exists |
| 4 | Test: pass in dummy dataclass objects, confirm JSON is written correctly | |
| 5 | Write `main.py` skeleton with placeholder `await` calls for all agents | No real logic yet — just the structure |

**✅ DoD:** `python agents/chronicler.py` (with hardcoded test data) writes a valid entry to `pattern_memory.json`.

---

#### FRONTEND / UI DEVELOPER
| # | Task | Notes |
|---|---|---|
| 1 | Create `frontend/index.html` with three panels: status banner, reasoning trace box, incident log table | Hardcoded placeholder content for now |
| 2 | Implement status banner with CSS classes for red/orange/green | `.status-down`, `.status-healing`, `.status-live` |
| 3 | Add a placeholder incident log row in the table | So it renders even without real data |
| 4 | Open in browser — confirm layout looks correct | |

**✅ DoD:** `index.html` opens in browser. All three panels visible. Status banner toggles between red/orange/green when CSS class is changed manually.

---

#### FOUNDRY IQ CONTEXT MANAGER
| # | Task | Notes |
|---|---|---|
| 1 | Write `knowledge_base/runbook.md` | Minimum 10 error scenarios — see role definition above |
| 2 | Write first draft of Diagnoser system prompt | Use template from SAD §4.2, customize |
| 3 | Test prompt manually: paste a fake log into ChatGPT or the Azure Playground | Does it return valid JSON? Does it stay on task? |
| 4 | Share runbook.md and system prompt draft with Giant for review | |

**✅ DoD:** `runbook.md` covers all 10 eval scenarios. System prompt returns valid JSON when tested manually in Azure AI Studio playground.

---

#### TECHNICAL WRITER & QA
| # | Task | Notes |
|---|---|---|
| 1 | Create `README.md` using the template in SUBMISSION_GUIDE.md | Fill section headers — content comes later |
| 2 | Write 10 QA test scenario descriptions (what to trigger, what to expect) | Plain English — no code |
| 3 | Create `eval/run_eval.py` skeleton | Just the scaffold — no logic yet |
| 4 | Open GitHub Issues for any immediate gaps you spot in the architecture | |

**✅ DoD:** README.md exists with all section headers. 10 QA scenarios documented.

---

#### CREATIVE DIRECTOR
| # | Task | Notes |
|---|---|---|
| 1 | Confirm or improve project name | Must sound professional in a pitch |
| 2 | Design logo (simple, ~30 min max) | Figma, Canva, or AI-generated — clean > complex |
| 3 | Define color palette: primary, secondary, accent | Share hex codes with Frontend Dev |
| 4 | Create pitch deck skeleton (8–10 slide headers) | See SUBMISSION_GUIDE.md for required slides |
| 5 | Share logo + colors in team chat | Frontend Dev needs these for dashboard theme |

**✅ DoD:** Logo file and color hex codes shared with team. Deck skeleton exists.

---

### DAY 1 — June 11, 2026
**Sprint Goal:** Full pipeline working from Watchman through Fixer. Diagnoser calling Azure AI Foundry and returning a thinking trace. FastAPI target server generating real crashes.

---

#### GIANT
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Write `agents/diagnoser.py` — complete Azure AI Foundry call | Use the code template from SAD §4.2 |
| 2 | ⚡ Test thinking extraction — confirm `thinking_trace` field is populated | Log it to console, check it's readable |
| 3 | ⚡ Wire Watchman → Diagnoser: pass `IncidentEvent` to `diagnoser.analyze()` | Confirm DiagnosisResult returns |
| 4 | Test with at least 3 different log scenarios (DB lock, 500, memory) | Does Diagnoser give different diagnoses? |
| 5 | Share `DiagnosisResult` example JSON with team | Everyone needs to understand this contract |
| 6 | 🤝 Review Context Manager's prompt refinements | Co-edit the system prompt based on test results |
| 7 | Evening sync | |

**✅ DoD:** Watchman detects a crash in the log → Diagnoser returns a `DiagnosisResult` with a non-empty `thinking_trace`. Confirmed in terminal output.

---

#### LEAD CLOUD ARCHITECT & DEVOPS
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Complete `target_server/server.py` — all crash endpoints working | Test each with `curl -X POST localhost:8000/crash/db-lock` |
| 2 | ⚡ Confirm server writes to `server.log` on each crash | Log format must match Watchman patterns |
| 3 | Write `/health` endpoint: returns `{"status": "online"}` normally | Fixer needs this to confirm recovery |
| 4 | Write `/recover` endpoint: sets server back to healthy state | Called by `clear_cache.sh` or `restart_service.sh` |
| 5 | 🤝 Align with Dev 2 on script names (must match ACTION_MAP exactly) | |

**✅ DoD:** `curl -X POST localhost:8000/crash/db-lock` writes DB_LOCK error to server.log. `/health` returns 200 when server is up.

---

#### AI AGENT DEV 1 — Watchman Integration
| # | Task | Notes |
|---|---|---|
| 1 | Integrate Watchman with the real FastAPI target server log output | Run both, trigger a crash, confirm Watchman fires |
| 2 | ⚡ Test full Watchman → Diagnoser handoff | Trigger crash → IncidentEvent → DiagnosisResult |
| 3 | Improve error pattern matching for edge cases | What if the log line format changes slightly? |
| 4 | Add logging to Watchman: `print(f"[WATCHMAN] Incident detected: {incident.incident_id}")` | |

**✅ DoD:** Trigger `/crash/db-lock` → Watchman fires within 10 seconds → Diagnoser receives IncidentEvent. Confirmed in terminal.

---

#### AI AGENT DEV 2 — Fixer Complete
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Write `confirm_recovery()` function — polls `/health` endpoint | Retries 10 times with 3-second interval |
| 2 | Complete all ACTION_MAP entries | All 6 actions must map to real scripts |
| 3 | Test: receive a real DiagnosisResult from Giant → execute action → confirm recovery | |
| 4 | Add logging: `print(f"[FIXER] Executing: {action_taken}")` | |
| 5 | Handle `escalate_to_human` case: log a warning, do not execute any script | |

**✅ DoD:** Given a `DiagnosisResult` with `recommended_action="restart_postgres"`, Fixer runs the script and `confirm_recovery()` returns True.

---

#### AI AGENT DEV 3 — Orchestration + Dashboard API
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Wire full `main.py`: Watchman → Diagnoser → Fixer → Chronicler | Use async/await |
| 2 | Add error handling: try/except around each agent call | If Diagnoser fails: log error, skip to Chronicler with error state |
| 3 | ⚡ Write `api/dashboard_api.py`: FastAPI serving `pattern_memory.json` as JSON | `GET /incidents` → returns all incidents |
| 4 | Add a `GET /status` endpoint: returns current server status + last incident | Frontend needs this |
| 5 | Test: run `main.py` against a triggered crash end-to-end | |

**✅ DoD:** `python main.py` runs. Trigger a crash. Pipeline completes Watchman → Diagnoser → Fixer → Chronicler. `GET /incidents` returns data.

---

#### FRONTEND / UI DEVELOPER
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Connect `app.js` to `dashboard_api.py` via `fetch()` polling every 3 seconds | `GET http://localhost:8001/incidents` |
| 2 | ⚡ Implement status banner logic: check last incident status → set CSS class | |
| 3 | Render incident log table rows dynamically from API response | |
| 4 | Add demo trigger button: `POST http://localhost:8000/crash/db-lock` | |
| 5 | 🤝 Apply color palette from Creative Director to dashboard | |

**✅ DoD:** Dashboard auto-updates within 3 seconds when `pattern_memory.json` changes. Demo trigger button causes status banner to flip to 🔴.

---

#### FOUNDRY IQ CONTEXT MANAGER
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Run refined system prompt with 5 different log scenarios | Test in Azure AI Studio playground |
| 2 | Fix any scenarios where Diagnoser returns wrong root_cause | Edit runbook.md entries for clarity |
| 3 | Test that confidence scores are reasonable (0.7–0.95 range) | If all return 0.99, prompt needs calibration |
| 4 | Write a "stress test log" — mix of ambiguous patterns to test edge cases | Hand to Technical Writer for QA |

**✅ DoD:** System prompt returns correct root_cause for 4/5 test scenarios without hallucinating action names.

---

#### TECHNICAL WRITER & QA
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Run first end-to-end QA test: trigger crash → watch full pipeline | Document what breaks |
| 2 | Log all bugs in GitHub Issues with steps to reproduce | |
| 3 | Write Architecture section of README.md | Pull from SAD §3 |
| 4 | Write Problem Statement section of README.md | |

**✅ DoD:** At least one end-to-end QA run completed. Bugs logged. README Architecture section drafted.

---

#### CREATIVE DIRECTOR
| # | Task | Notes |
|---|---|---|
| 1 | Build complete pitch slide deck (8–10 slides with content) | Use template from SUBMISSION_GUIDE.md |
| 2 | Draft word-for-word 5-minute demo script | Section breakdown in SUBMISSION_GUIDE.md |
| 3 | Coordinate with Frontend Dev on dashboard screenshot for slides | |

**✅ DoD:** Pitch deck complete with content. Demo script drafted.

---

### DAY 2 — June 12, 2026
**Sprint Goal:** System is fully integrated end-to-end. Dashboard live. Full pipeline demo runs cleanly three times in a row.

---

#### GIANT
| # | Task | Notes |
|---|---|---|
| 1 | Run full system demo end-to-end 3 times | Fix anything that breaks |
| 2 | Review `thinking_trace` quality — is it readable? impressive? | If not, refine system prompt with Context Manager |
| 3 | Write evaluation harness spec in `eval/run_eval.py` | Script that runs all 10 scenarios automatically |
| 4 | Review Technical Writer's README draft | |
| 5 | Identify any "wow" moments missing from the demo | Raise in evening sync |
| 6 | Evening sync — integration review | |

**✅ DoD:** System runs cleanly 3 consecutive times. Eval harness runs at least 5/10 scenarios automatically.

---

#### LEAD CLOUD ARCHITECT & DEVOPS
| # | Task | Notes |
|---|---|---|
| 1 | Ensure all teammates can `git pull` + `python main.py` and it runs | Clean onboarding test |
| 2 | Add all 3 crash types to target server (db-lock, 500, memory) | Test each writes distinct log patterns |
| 3 | Clean up bash scripts — ensure they call `/recover` on the server after restart | Fixer confirmation must work |
| 4 | Write setup instructions for README (Quick Start section) | |

---

#### AI AGENT DEV 1 + DEV 2 + DEV 3
| # | Task | Notes |
|---|---|---|
| 1 | Bug-fix day — work through GitHub Issues list from QA | Prioritize anything that breaks the demo |
| 2 | Dev 3: Add `GET /current-trace` endpoint to Dashboard API | Returns the current in-progress thinking_trace while Diagnoser is running |
| 3 | Dev 1: Test Watchman does not fire duplicate incidents within 30 seconds | Debounce logic |
| 4 | Dev 2: Test that Fixer handles a slow-recovering server gracefully | confirm_recovery timeout case |

---

#### FRONTEND / UI DEVELOPER
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Implement live reasoning trace streaming | Poll `GET /current-trace` and render character-by-character |
| 2 | Add agent activity rail: Watchman → Diagnoser → Fixer → Chronicler with visual progress | |
| 3 | Add pattern stats cards (total incidents, avg time, success rate) from `pattern_summary` | |
| 4 | Final dashboard polish: dark theme, clean typography, status animations | |

**✅ DoD:** Dashboard shows live reasoning trace appearing as Diagnoser runs. All 5 panels populated with real data.

---

#### FOUNDRY IQ CONTEXT MANAGER
| # | Task | Notes |
|---|---|---|
| 1 | Final system prompt version — no more changes after today | |
| 2 | Complete all 10 runbook entries — QA each against Diagnoser | |
| 3 | Document prompt design decisions (why each instruction is in the prompt) | Giant includes this in README |

---

#### TECHNICAL WRITER & QA
| # | Task | Notes |
|---|---|---|
| 1 | ⚡ Run all 10 QA test scenarios — document results in eval sheet | |
| 2 | Write full README.md — all sections complete except Demo Video link | |
| 3 | Verify GitHub repo structure matches SAD §8 exactly | |

---

#### CREATIVE DIRECTOR
| # | Task | Notes |
|---|---|---|
| 1 | Finalize pitch deck — all slides done, reviewed by Giant | |
| 2 | Record demo video draft (rough cut) | Use OBS or Loom |
| 3 | Share rough cut in team chat for feedback | |

---

### DAY 3 — June 13, 2026
**Sprint Goal:** Demo video recorded and polished. README finalized. Submission package reviewed.

---

| Role | Task |
|---|---|
| **Giant** | Review final README, review pitch script, record voiceover for demo video, sign off on submission package |
| **Cloud Architect** | Final repo cleanup — delete temp files, ensure `.env` is not committed, update `.gitignore` |
| **All Devs** | Final bug fixes only. No new features. Polish logging output for video clarity |
| **Frontend Dev** | Record screen of full demo dashboard during a live pipeline run |
| **Context Manager** | Final review of runbook.md — is it presentable in the repo? |
| **Technical Writer** | Finalize README.md, write submission description text (see SUBMISSION_GUIDE.md §4) |
| **Creative Director** | ⚡ Record and edit final 5-minute demo video. Upload to YouTube (unlisted) or as MP4 |
| **Project Director (Giant)** | Review complete submission checklist from SUBMISSION_GUIDE.md |

---

### DAY 4 — June 14, 2026 (SUBMISSION DAY)
**Deadline: 11:59 PM PT. Target submission: 5:00 PM PT (safety margin)**

| Time (PT) | Task | Owner |
|---|---|---|
| 9:00 AM | Final team sync — confirm all items on submission checklist | Giant |
| 10:00 AM | One last full system demo run — confirm everything still works | All Devs |
| 11:00 AM | Technical Writer finalizes README.md | Technical Writer |
| 12:00 PM | Upload demo video to YouTube (unlisted) — copy link into README | Creative Director |
| 1:00 PM | Giant reviews complete GitHub repo — every file in place | Giant |
| 2:00 PM | Submit to hackathon platform | Giant |
| 3:00 PM | ✅ SUBMITTED — team celebration | Everyone |

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Azure student subscription has quota limits (model calls/min) | HIGH | HIGH | Test quota Day 0. Add `time.sleep(1)` between Diagnoser calls if needed. |
| Diagnoser returns malformed JSON | MEDIUM | HIGH | `response_format: json_object` + try/except fallback in diagnoser.py |
| Frontend partner unavailable on Day 2 | LOW | HIGH | Dev 3 builds a minimal Streamlit dashboard as fallback |
| Model deployment naming mismatch | MEDIUM | MEDIUM | MODEL_DEPLOYMENT_NAME in .env must match exactly the Foundry deployment name |
| Pipeline fails during demo video recording | MEDIUM | HIGH | Pre-record 3 takes. Use the cleanest one. |
| Team member goes silent after Day 0 | MEDIUM | MEDIUM | Giant can absorb most backend tasks solo if needed (TAI architecture experience) |
| Thinking trace is too short / unimpressive | LOW | HIGH | Adjust system prompt to require longer step-by-step explanations |

---

## 8. Success Criteria

### Technical Success (Minimum to Submit)
- [ ] Watchman detects ERROR 500 from server.log within 10 seconds
- [ ] Diagnoser returns a non-empty `thinking_trace` from Azure AI Foundry
- [ ] Fixer executes a remediation script correctly
- [ ] Chronicler writes to `pattern_memory.json`
- [ ] Dashboard shows live status and at least one completed incident

### Competitive Success (To Win)
- [ ] Diagnoser reasoning trace is readable, multi-step, and clearly shows *why* the action was chosen
- [ ] Evaluation harness shows ≥ 80% accuracy across 10 scenarios
- [ ] Dashboard displays the live thinking trace as it generates
- [ ] README clearly maps each system component to the Reasoning Agents track criteria
- [ ] Demo video shows a crash-to-recovery in under 60 seconds with narration

### Stretch Goals (If Ahead of Schedule)
- [ ] Chronicler detects recurring patterns ("this is the 3rd DB_LOCK in 24 hours") and surfaces in dashboard
- [ ] Diagnoser confidence < 0.6 → triggers a simulated human alert (Slack webhook mock)
- [ ] Multiple crash scenario types demoed in the video (not just DB lock)

---

## 9. Open Design Issues

| Issue | Status | Owner | Deadline |
|---|---|---|---|
| Confirm which model is available in student subscription (o-series vs gpt-4o) | ✅ RESOLVED — using gpt-4.1 | Giant | Day 0 evening |
| Dashboard: WebSocket vs polling (3s interval) | ⏳ OPEN (Phase 2) | Frontend Dev | Day 1 |
| runbook.md: how many entries minimum for demo to look credible | ✅ RESOLVED — 4 runbooks + SOP | Context Manager | Day 0 |
| Evaluation: run automatically in CI vs run manually | ⏳ OPEN | Technical Writer | Day 2 |

---

## 10. Roadmap (Post-Pipeline)

| Priority | Item | Status |
|---|---|---|
| 1 | Dashboard — Flask/FastAPI backend + HTML/JS frontend | Phase 2 |
| 2 | Additional failure types (service_crash, cascading_failure, timeout) | Phase 2 |
| 3 | Evaluation harness (eval/run_eval.py with 10 scenarios) | Phase 2 |
| 4 | Demo video (5-min screen recording of full pipeline) | Required for submission |
| 5 | Containerization (Dockerfile + Azure Container Apps) | Post-hackathon |

---

*PDR v1.1 — SRE Flight Crew — Agents League 2026 (updated: model confirmed as gpt-4.1)*
