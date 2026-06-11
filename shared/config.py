"""Central configuration. Loads .env once; everything else imports from here.

Team contract: NEVER call os.getenv() directly in agent files.
Import what you need from this module instead.

Change log:
  - [DevOps]  Initial config: mock server, health check, logs, dashboard
  - [Ochuko]  Added: Azure AI Foundry agent config, knowledge base,
              pattern memory, watchman interval, diagnoser threshold
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# --- Azure AI Foundry ---
AZURE_PROJECT_ENDPOINT = _get("AZURE_PROJECT_ENDPOINT")
AZURE_SUBSCRIPTION_ID = _get("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP = _get("AZURE_RESOURCE_GROUP")
MODEL_DEPLOYMENT_NAME = _get("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
<<<<<<< HEAD
DIAGNOSER_AGENT_NAME = _get("DIAGNOSER_AGENT_NAME", "DIAGNOSER")
DIAGNOSER_AGENT_VERSION = _get("DIAGNOSER_AGENT_VERSION", "1")
=======
DIAGNOSER_AGENT_ID = _get("DIAGNOSER_AGENT_ID")
DIAGNOSER_AGENT_NAME = _get("DIAGNOSER_AGENT_NAME", "DIAGNOSER")
DIAGNOSER_AGENT_VERSION = _get("DIAGNOSER_AGENT_VERSION", "5")

# --- Knowledge base (runbook files for Diagnoser file_search) ---
KNOWLEDGE_BASE_DIR = _get(
    "KNOWLEDGE_BASE_DIR",
    str(PROJECT_ROOT / "agents" / "diagnoser" / "knowledge_base"),
)

# --- Diagnoser tuning ---
DIAGNOSER_ESCALATION_THRESHOLD = float(
    _get("DIAGNOSER_ESCALATION_THRESHOLD", "0.6")
)

# --- Pattern memory (Chronicler) ---
PATTERN_MEMORY_PATH = _get(
    "PATTERN_MEMORY_PATH",
    str(PROJECT_ROOT / "data" / "pattern_memory.json"),
)
>>>>>>> 7164f4d6a6f74c682323897fbdace8cd9fae780d

# --- Simulated target server ---
MOCK_SERVER_HOST = _get("MOCK_SERVER_HOST", "127.0.0.1")
MOCK_SERVER_PORT = int(_get("MOCK_SERVER_PORT", "8090"))
MOCK_SERVER_URL = f"http://{MOCK_SERVER_HOST}:{MOCK_SERVER_PORT}"
HEALTH_CHECK_URL = _get("HEALTH_CHECK_URL", f"{MOCK_SERVER_URL}/health")
HEALTH_CHECK_INTERVAL_SECONDS = float(_get("HEALTH_CHECK_INTERVAL_SECONDS", "2"))
WATCHMAN_POLL_INTERVAL_SEC = float(_get("WATCHMAN_POLL_INTERVAL_SEC", "3"))

# --- Watchman ---
WATCHMAN_POLL_INTERVAL_SEC = float(_get("WATCHMAN_POLL_INTERVAL_SEC", "3"))

# --- Logs ---
SERVER_LOG_PATH = PROJECT_ROOT / _get("SERVER_LOG_PATH", "logs/server.log")

# --- Dashboard ---
DASHBOARD_PORT = int(_get("DASHBOARD_PORT", "5000"))
