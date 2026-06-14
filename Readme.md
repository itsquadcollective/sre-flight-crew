# 🚀 Self-Healing SRE Flight Crew

An automated AI-driven SRE agent framework built to detect, diagnose, and heal production incidents using intelligent runbook knowledge retrieval.

---

## 🛠️ Current Architecture

Our system is backed by a complete Knowledge Base and optimized prompts deployed via Azure AI Foundry. It handles end-to-end incident mitigation:
1. **Watchman:** Detects anomalies and live production incidents.
2. **Diagnoser:** Analyzes error footprints, maps them to locked system runbooks, and returns structured JSON fixes.
3. **Fixer:** Executes the recommended recovery action instantly.

---

## 📖 Covered Scenarios & Runbooks

The framework is strictly locked and verified for the following production failure modes:

| Incident Key | Target Runbook | Expected Resolution | Target Confidence |
| :--- | :--- | :--- | :--- |
| `DB_CRASH` | `docs/runbook_db_crash.md` | `restart_db` | 0.70 - 0.95 |
| `MEMORY_SPIKE` | `docs/runbook_memory_spike.md` | `clear_cache` | 0.70 - 0.95 |

---

## 📊 Automated Evaluation Harness

We maintain an automated test harness to rigorously validate the accuracy, constraint compliance, and latency of our Diagnoser engine.

### How to Run the Evaluation
To execute the test suite against the active production scenarios, run the following command from the repository root:

```bash
python eval/run_eval.py
