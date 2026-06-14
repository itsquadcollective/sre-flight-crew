# Final Technical Submission Guide
## Project: Self-Healing SRE Flight Crew
### Agents League – AI Skills Fest 2026 | Reasoning Agents Track

**Version:** 1.0 | **Date:** June 10, 2026 | **Owner:** Technical Writer

---

## 1. Hackathon Submission Requirements

### 1.1 Key Deadlines

| Event | Date & Time |
|---|---|
| Registration Close | June 12, 2026 – 12:00 PM PT |
| Submission Deadline | June 14, 2026 – 11:59 PM PT |
| **Target Submit Time** | **June 14, 2026 – 5:00 PM PT** (safety buffer) |

### 1.2 Track Requirements: Reasoning Agents

The judges evaluate submissions on these criteria. Every section of your README and your demo video must map explicitly to at least one of these:

| Criterion | How Our System Satisfies It |
|---|---|
| **Multi-step reasoning** | Diagnoser produces a step-by-step chain-of-thought: log analysis → pattern matching → root cause → action selection |
| **Complex problem solving** | Server downtime is a multi-variable problem (error type × service state × runbook match) — not solvable by a simple rule |
| **Use of Microsoft Foundry** | All AI inference runs through Azure AI Foundry (`AIProjectClient` + `DefaultAzureCredential`) |
| **Agent autonomy** | Zero human input from crash detection to recovery — the system acts entirely on its own |
| **Practical real-world application** | Downtime = lost revenue. The problem is universally understood and the impact is measurable |

### 1.3 What You Must Submit

- [ ] **GitHub Repository** — public, clean, all code present
- [ ] **README.md** — complete (use template in §3 below)
- [ ] **Demo Video** — 5 minutes, shows the full pipeline live
- [ ] **Submission Form** — filled on the hackathon platform with: project name, GitHub URL, demo video URL, track selection, team members

---

## 2. GitHub Repository Checklist

Before submitting, verify the repository passes every item below.

### 2.1 Repository Structure Check

```
self-healing-sre/
├── ✅ README.md                      (complete — see §3)
├── ✅ requirements.txt               (all packages listed with versions)
├── ✅ .env.example                   (all vars listed, no real values)
├── ✅ .gitignore                     (.env, __pycache__, server.log, *.pyc)
├── ✅ main.py                        (orchestrator — runs the full pipeline)
├── ✅ agents/
│   ├── ✅ watchman.py
│   ├── ✅ diagnoser.py
│   ├── ✅ fixer.py
│   └── ✅ chronicler.py
├── ✅ target_server/
│   ├── ✅ server.py                  (FastAPI with crash endpoints)
│   └── ✅ log_simulator.py           (generates fake logs)
├── ✅ agents/diagnoser/knowledge_base
│   └── ✅ runbook_db_crash.md
        ✅ runbook_memory_spike.md  
├── ✅ scripts/
│   ├── ✅ restart_service.sh
│   ├── ✅ clear_db_lock.sh
│   └── ✅ clear_cache.sh
├── ✅ data/
│   └── ✅ pattern_memory.json        (sample data pre-populated for judges)
├── ✅ api/
│   └── ✅ dashboard_api.py
├── ✅ frontend/
│   ├── ✅ index.html
│   ├── ✅ app.js
│   └── ✅ styles.css
├── ✅ eval/
│   └── ✅ run_eval.py                (10-scenario eval harness)
└── ✅ docs/
    ├── ✅ SAD.md
    ├── ✅ PDR.md
    └── ✅ SUBMISSION_GUIDE.md
```

### 2.2 Security Checklist (CRITICAL — Disqualification Risk)

- [ ] `.env` file is NOT committed (check `git log --all -- .env`)
- [ ] No API keys appear anywhere in any Python file
- [ ] No Azure subscription ID appears in any committed file
- [ ] `AZURE_AI_FOUNDRY_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` only appear in `.env.example` as empty placeholders

### 2.3 Code Quality Checklist

- [ ] `python main.py` runs without syntax errors
- [ ] `pip install -r requirements.txt` succeeds on a clean environment
- [ ] All imports resolve (no broken relative imports)
- [ ] No hardcoded local file paths (use `os.path.join` or env vars)
- [ ] `pattern_memory.json` in repo contains sample data so judges can see the format immediately

---

## 3. README.md Template

> Copy this exactly. Fill every section before submission. Sections marked ⭐ are seen first by judges — make them excellent.

---

```markdown
# 🛠️ Self-Healing SRE Flight Crew
### Autonomous Multi-Agent Server Recovery System

> An AI-powered system that detects server failures, reasons through the root cause using 
> Azure AI Foundry, and automatically remediates the incident — in under 60 seconds.

**Hackathon:** Agents League – AI Skills Fest 2026  
**Track:** Reasoning Agents  
**Team:** [List team member names]  
**Demo Video:** [YouTube/Loom link]

---

## ⭐ The Problem

[2–3 sentences. Make it visceral. "A server crash at 3 AM costs $5,600 per minute. 
A human engineer takes 15–45 minutes to diagnose and fix it manually. 
Small teams often have no on-call engineer at all."]

## ⭐ Our Solution

[2–3 sentences. "The Self-Healing SRE Flight Crew is a 4-agent system that..."]

## ⭐ How It Works (The Reasoning Chain)

Explain the 4-agent pipeline and why it qualifies as multi-step reasoning:

1. **WATCHMAN (Agent 1)** — [what it does]
2. **DIAGNOSER (Agent 2)** — [what it does — emphasize thinking trace]  
3. **FIXER (Agent 3)** — [what it does]
4. **CHRONICLER (Agent 4)** — [what it does]

Include the architecture diagram from SAD §3.1 here.

## ⭐ The Reasoning in Action (Sample Output)

Paste a real example of the Diagnoser's thinking_trace here. 
This is what judges will look for first.

```json
{
  "thinking_trace": "Step 1: Examined log lines 16-20. Found repeated DB_LOCK errors originating at 03:14:22Z, 
    frequency: 4 errors in 3 seconds, all on /api/data endpoint.\n
    Step 2: Cross-referenced runbook §2. Pattern matches 'PostgreSQL connection pool exhaustion'.\n
    Step 3: Secondary signals: no memory overflow indicators, port conflict ruled out.\n
    Step 4: Recommended action: restart_postgres. Confidence: 94%.",
  "root_cause": "database_lock",
  "confidence": 0.94,
  "recovery_action": "restart_db"
}
```

## Azure AI Foundry Integration

- **Project:** [your foundry project name]
- **Model:** gpt-4.1
- **SDK:** `azure-ai-projects` with `DefaultAzureCredential`
- **Feature Used:** [model inference with thinking extraction / json_object response format]

## Evaluation Results

| Metric | Result |
|---|---|
| Root Cause Accuracy | X/10 (X%) |
| Action Selection Accuracy | X/10 (X%) |
| Average Recovery Time | X seconds |
| JSON Parse Success Rate | 100% |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/[YOUR-ORG]/self-healing-sre.git
cd self-healing-sre

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your Azure AI Foundry endpoint and model deployment name

# 4. Authenticate with Azure
az login

# 5. Start the simulated server
uvicorn target_server.server:app --port 8000 &

# 6. Start the dashboard API
uvicorn api.dashboard_api:app --port 8001 &

# 7. Open the dashboard
open frontend/index.html   # or double-click index.html

# 8. Run the agent pipeline
python main.py

# 9. Trigger a crash (in another terminal)
curl -X POST http://localhost:8000/crash/db-lock
```

## Architecture

[Link to SAD.md in the docs/ folder]

## Team

| Name | Role |
|---|---|
| [Name] | Lead Architect |
| [Name] | Cloud Architect & DevOps |
| [Name] | AI Agent Dev (Watchman/Diagnoser) |
| [Name] | AI Agent Dev (Fixer) |
| [Name] | AI Agent Dev (Orchestration/Chronicler) |
| [Name] | Frontend Developer |
| [Name] | Context Manager |
| [Name] | Technical Writer & QA |
| [Name] | Creative Director |

## License

MIT
```

---

## 4. Demo Video Guide

### 4.1 Technical Requirements
- Length: **exactly 5 minutes** (do not go over)
- Format: MP4 or YouTube unlisted link
- Resolution: minimum 1080p
- Audio: narration required (Project Director voiceover)
- Screen recording: dashboard must be clearly visible

### 4.2 Five-Minute Script Structure

**Segment 1: Hook (0:00 – 0:30)**  
Open on the Problem. Do not start with team introductions.

> "It's 3 AM. Your server just crashed. Every minute of downtime costs $5,600. 
> And your only engineer is asleep. What do you do?  
> That's the problem we solved."

Cut to: dashboard showing 🔴 SERVER DOWN.

---

**Segment 2: System Overview (0:30 – 1:30)**  
Walk through the 4-agent architecture. Screen should show the architecture diagram from SAD.

> "Meet the Self-Healing SRE Flight Crew. Four AI agents that work together 
> to detect, diagnose, fix, and remember server failures — automatically."

Briefly name each agent and its role. 20 seconds each.

---

**Segment 3: Live Demo (1:30 – 3:30) — THE CRITICAL SEGMENT**  
This is what wins or loses the submission. Go slow. Let the reasoning trace appear on screen.

> "Let me show you this live."

Steps to demo on screen:
1. Show dashboard with 🟢 SERVER LIVE
2. Click the "Trigger Crash" button
3. Watch status flip to 🔴 SERVER DOWN
4. Point to the agent activity rail: "Watchman just detected the crash — it's passing the incident to the Diagnoser"
5. Watch the reasoning trace appear live: "Watch the AI reason through this step by step..."
6. Read 2–3 lines of the thinking trace aloud. Pause. Let it sink in.
7. "It matched the pattern to our runbook. Database lock. 94% confidence. It's calling the Fixer."
8. Watch status flip to 🟠 AGENTS HEALING
9. Watch recovery: status flips to 🟢 SERVER LIVE
10. Point to incident log: "The Chronicler just logged the full incident — cause, action, duration, reasoning trace."

---

**Segment 4: Results + Evaluation (3:30 – 4:30)**  
Show the eval results. This is your credibility segment.

> "We didn't just build this — we tested it."

Show `run_eval.py` output on screen briefly. Talk through the results table.

> "Across 10 different crash scenarios: 9 out of 10 correct diagnoses. 
> Average recovery time: under 30 seconds."

---

**Segment 5: Close (4:30 – 5:00)**

> "This is what Azure AI Foundry makes possible. Not just alerts. 
> Not just automation. Real reasoning, real remediation, real-time.  
> The Self-Healing SRE Flight Crew. Available while you sleep."

Cut to: logo on dark background. Team names.

---

### 4.3 Recording Checklist

Before you hit record:
- [ ] Dashboard is open in full-screen browser
- [ ] Both servers (`server.py` and `dashboard_api.py`) are running
- [ ] `main.py` is running and waiting for an incident
- [ ] Font size in terminal is large enough to be readable in video
- [ ] No personal information visible on screen (browser bookmarks, notifications off)
- [ ] Dark mode on browser (matches dashboard theme)
- [ ] Rehearsed the demo at least 3 times

---

## 5. Track Criteria Alignment Matrix

Use this table to verify your submission hits every judging criterion. Reference this in your README.

| Judging Criterion | What We Built | Where to See It |
|---|---|---|
| Multi-step reasoning | Diagnoser produces 3+ explicit reasoning steps before selecting an action | `agents/diagnoser.py` → `thinking_trace` field |
| Use of Microsoft Foundry | All AI inference via `AIProjectClient` + `DefaultAzureCredential` | `agents/diagnoser.py` |
| Complex problem-solving | Diagnosis requires cross-referencing error patterns with runbook + confidence scoring | `knowledge_base/runbook.md` + Diagnoser system prompt |
| Agent autonomy | Zero human input required — pipeline runs end-to-end from detection to memory | `main.py` |
| Real-world application | Server downtime is a universally understood, measurable problem | README Problem Statement |
| Technical implementation quality | 4 typed agents, evaluation harness, architecture documentation | All of `agents/`, `eval/`, `docs/` |
| Demo clarity | Dashboard shows reasoning trace live; demo video narrates each step | `frontend/`, demo video |

---

## 6. Submission Description Text

> Use this as the short description when filling the submission form.

```
The Self-Healing SRE Flight Crew is an autonomous 4-agent system built on 
Azure AI Foundry that detects server failures, diagnoses root causes through 
multi-step AI reasoning, executes automated remediation, and builds pattern 
memory — all without human intervention.

Unlike traditional monitoring tools that only alert engineers, our system 
reasons through the problem: Agent 2 (the Diagnoser) uses an Azure AI 
o-series model to analyze error logs, cross-reference a knowledge base, and 
produce a transparent chain-of-thought before selecting the correct fix. The 
full reasoning trace is displayed live on a real-time dashboard.

Built with Python, Azure AI Foundry (AIProjectClient + DefaultAzureCredential), 
and FastAPI. Includes a 10-scenario evaluation harness demonstrating X% 
diagnostic accuracy and sub-60-second recovery times.
```

> **Before submitting:** replace `X%` with your actual eval result.

---

## 7. Final Submission Checklist

### Repository
- [ ] Repo is public on GitHub
- [ ] All code committed and pushed
- [ ] `.env` not committed (CRITICAL)
- [ ] `README.md` complete (all sections filled)
- [ ] `pattern_memory.json` contains sample data
- [ ] `eval/run_eval.py` runs and outputs results
- [ ] `docs/SAD.md`, `docs/PDR.md`, `docs/SUBMISSION_GUIDE.md` all present

### Demo Video
- [ ] Video is exactly 5 minutes (±15 seconds)
- [ ] All 5 segments present (Hook, Overview, Demo, Eval, Close)
- [ ] Live reasoning trace is visible and readable on screen
- [ ] Full crash-to-recovery cycle shown
- [ ] Video link added to README.md

### Technical
- [ ] System runs `python main.py` without errors on a clean clone
- [ ] Evaluation results are in README table
- [ ] Azure AI Foundry is the AI provider (not OpenAI direct)
- [ ] `thinking_trace` appears in at least one JSON sample in README

### Submission Form
- [ ] Project name filled
- [ ] GitHub URL filled
- [ ] Demo video URL filled
- [ ] Track: "Reasoning Agents" selected
- [ ] All team members listed
- [ ] Submitted before 5:00 PM PT on June 14

---

## 8. If Something Breaks on Submission Day

### Scenario: Azure Foundry is down / quota exceeded
**Fix:** Pre-record the demo video on June 13 when everything works. Submit the video even if you can't run live on June 14. The video is the submission.

### Scenario: Dashboard won't load
**Fix:** The backend pipeline is the actual submission — not the frontend. Run `python main.py` in the terminal with verbose logging and screen-record the terminal output. It's less pretty but it demonstrates the reasoning.

### Scenario: Diagnoser returns invalid JSON
**Fix:** The `response_format: json_object` API parameter should prevent this. If it still fails, add a fallback in `diagnoser.py` that retries once with the instruction: "Your last response was not valid JSON. Return only JSON, no other text."

### Scenario: GitHub repo goes private / inaccessible
**Fix:** Double-check repo visibility setting before submitting. Keep the repo URL bookmarked and test it in an incognito window.

---

*SUBMISSION_GUIDE v1.0 — Self-Healing SRE Flight Crew — Agents League 2026*
