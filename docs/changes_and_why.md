# Changes and Why — SRE Flight Crew

This document explains what code from the team's builds was changed, why,
and what was preserved. Our priority is **reliability and maintainability**,
and we build on top of the team's work wherever possible.

---

## Summary of Team Code Preserved (Unchanged)

| File | Author | Status |
|---|---|---|
| `shared/schemas.py` | Team (DevOps) | **Preserved** — only added `"escalate_to_human"` to recovery_action Literal |
| `shared/event_bus.py` | Team (DevOps) | **Preserved** — unchanged, used as-is by main.py |
| `simulator/mock_server.py` | Team (DevOps) | **Preserved** — unchanged, Fixer calls its HTTP API |
| `simulator/failure_injector.py` | Team (DevOps) | **Preserved** — unchanged |
| `tests/test_event_bus.py` | Team (DevOps) | **Preserved** — all 4 tests still pass |
| `tests/test_simulator.py` | Team (DevOps) | **Preserved** — all 8 tests still pass |
| `agents/fixer/recovery_scripts/*.sh` | Team (DevOps) | **Preserved** — kept for reference, Linux users |
| `docs/DEV_SETUP.md` | Team | **Preserved** — unchanged |
| `.gitignore` | Team | **Preserved** — unchanged |

---

## Files Modified (with rationale)

### `shared/config.py` — Rewritten

**What changed:** Expanded from 8 vars to 18 vars.

**Why:** The team's original config covered only mock server and dashboard.
The pipeline needs: MODEL_DEPLOYMENT_NAME, DIAGNOSER_AGENT_ID, KNOWLEDGE_BASE_DIR,
PATTERN_MEMORY_PATH, WATCHMAN_POLL_INTERVAL_SEC, DIAGNOSER_ESCALATION_THRESHOLD,
MOCK_SERVER_URL (computed), SERVER_LOG_PATH.

**What was preserved:** All original env var names and defaults are maintained.
Any code that imported from config.py before will still work.

---

### `shared/schemas.py` — Modified (1 line)

**What changed:** Added `"escalate_to_human"` to `DiagnosisResult.recovery_action` Literal.

**Why:** The Diagnoser's 3-layer reasoning strategy needs an escalation path
when confidence is below 0.6. Without this, the schema would reject the
Diagnoser's legitimate "I don't know" response.

**What was preserved:** All existing fields, all existing Literal values,
all existing dataclasses. Purely additive change.

---

### `.env` and `.env.example` — Updated

**What changed:** Added `MODEL_DEPLOYMENT_NAME=gpt-4.1`, fixed
`HEALTH_CHECK_URL` port from 8080 to 8090, added watchman/log config.

**Why:** Port 8080 is blocked on Windows (Hyper-V reserved range, as noted
in DEV_SETUP.md). The mock server defaults to 8090. The health check URL
must match.

---

### `docs/SAD.md` — Modified (3 lines)

**What changed:** Replaced `o-series or gpt-4o` with `gpt-4.1` in 3 places.

**Why:** User directive — the confirmed model deployment name is `gpt-4.1`.
Docs must match the actual deployment.

---

### `docs/PDR.md` — Modified (6 lines + roadmap section)

**What changed:**
- Decision 4 title: `o-series` → `gpt-4.1`
- Task table: `Deploy an o-series or gpt-4o model` → `Deploy a gpt-4.1 model`
- Risk table: updated model mismatch risk
- Closed 2 resolved design issues (model choice, runbook count)
- Added Section 10: Roadmap (dashboard, evaluation, demo video, containerization)

**Why:** Keep the PDR aligned with actual decisions. The dashboard and
containerization roadmap were explicitly requested by the PM.

---

### `docs/SUBMISSION_GUIDE.md` — Modified (1 line)

**What changed:** Model placeholder → `gpt-4.1`.

**Why:** Consistency with the deployed model.

---

## Files Replaced (with rationale)

### `agents/watchman/watchman_agent.py` — Replaced

**Original (team, commit f96d66c):** 14-line stub that returned a HARDCODED
`ErrorEvent` with `error_type="DB_CRASH"` and a fixed message every time.

**Why replaced:** A hardcoded stub cannot drive a real pipeline. The Watchman
must actually read `logs/server.log` and detect errors dynamically for the
pipeline to be autonomous (a hackathon judging criterion).

**What was preserved from the team's stub:**
- The `ErrorEvent` dataclass contract (shared/schemas.py) — unchanged
- The `event_id` format: `evt_YYYYMMDD_HHMMSS_NNN`
- The class name: `WatchmanAgent`
- The import pattern

**What's new:**
- Async file-position-tracking log tailer
- Pattern matching via `log_parser.py` (new utility module)
- Debounce: suppresses duplicate alerts within 30s
- Rolling snippet buffer for log context
- `monitor()` method that blocks until error found

---

### `agents/diagnoser/diagnoser_agent.py` — Written (was empty on dev)

**Original (dev branch):** Empty file (0 bytes). The team created the stub
file but did not implement the Diagnoser.

**Source:** Code was developed on the `ochukos-starter` branch, tested with
31 passing unit tests, then brought to `dev` with fixes for:
- UTF-8 encoding (Unicode box-drawing characters)
- Removed `sys.path.insert(0, ...)` hack (unnecessary with proper imports)
- Updated to use the new **Responses API** (`openai_client.responses.create` with `agent_reference` in `extra_body`) to allow seamless integration with manually created portal agents (configured with name `DIAGNOSER` and version `5`) without managing threads, runs, and polling loop in Python.

---

### `agents/diagnoser/setup_agent.py` — Written (was empty on dev)

**Original (dev branch):** Empty file.

**Source:** From `ochukos-starter` branch, updated for azure-ai-projects v2.x
SDK. The v2 SDK uses `project_client.get_openai_client()` which returns a
standard `AsyncOpenAI` client. File upload uses `openai_client.files.create()`
with `purpose="assistants"`, not the old `FilePurpose.AGENTS` enum.

---

### `agents/fixer/fixer_agent.py` — Written (was empty on dev)

**Original (dev branch):** Empty file.

**Design note:** Uses HTTP calls to the mock server's `/sim/recover/{action}`
endpoint instead of bash scripts. The team's `recovery_scripts/*.sh` files
are preserved for reference, but the Fixer calls HTTP directly for
cross-platform reliability (Windows has no bash without Git Bash/WSL).

---

### `main.py` — Written (was empty on dev)

**Original (dev branch):** Empty file.

**Design:** Wires all 4 agents in an async loop. The Chronicler is inline
(simple JSON append to `pattern_memory.json`) rather than a separate class,
because its logic is ~30 lines. Can be extracted later if it grows.

---

## New Files Added

| File | Purpose |
|---|---|
| `agents/watchman/log_parser.py` | Utility: parse mock server log lines, classify error types |
| `agents/diagnoser/knowledge_base/sop_general.md` | System architecture doc for open-ended reasoning |
| `agents/diagnoser/prompt_templates.py` | Agent instructions + incident message builder |
| `data/pattern_memory.json` | Seed data for Chronicler's incident memory |

---

## Virtual Environment

A `.venv/` directory was created to isolate dependencies and resolve the
`RequestsDependencyWarning` about mismatched urllib3/chardet versions in the
system Python. Use `.venv/Scripts/python.exe` (Windows) to run the project.

---

*Document created: 2026-06-11 | Author: Ochuko (PM + Azure AI Engineer)*
