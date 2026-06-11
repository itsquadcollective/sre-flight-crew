# agents/diagnoser/setup_agent.py
# ─────────────────────────────────────────────────────────────────────────────
# SETUP SCRIPT — Deploy the Diagnoser agent to Azure AI Foundry
#
# This script creates the Diagnoser agent in Foundry with:
#   1. Agent instructions (from prompt_templates.py)
#   2. File Search tool with runbook vector store attached
#   3. Response format set to JSON
#
# Uses azure-ai-projects v2.x API:
#   project_client.get_openai_client() → standard OpenAI Assistants API
#   (client.files, client.vector_stores, client.beta.assistants)
#
# Run this ONCE before starting the pipeline. It prints the DIAGNOSER_AGENT_ID
# that you must add to your .env file.
#
# Usage:
#   python agents/diagnoser/setup_agent.py           # create new agent
#   python agents/diagnoser/setup_agent.py --update   # update existing agent
#
# After running, copy the printed agent ID into your .env:
#   DIAGNOSER_AGENT_ID=asst_xxxxxxxxxxxxx
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import sys
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

from shared.config import (
    AZURE_PROJECT_ENDPOINT,
    MODEL_DEPLOYMENT_NAME,
    KNOWLEDGE_BASE_DIR,
)
from agents.diagnoser.prompt_templates import DIAGNOSER_AGENT_INSTRUCTIONS


async def deploy_diagnoser_agent() -> str:
    """
    Deploy the Diagnoser agent to Azure AI Foundry.

    Steps:
        1. Upload all runbook .md files to Foundry via OpenAI files API
        2. Create a vector store from the uploaded files
        3. Create the assistant with instructions + file_search tool
        4. Return the agent ID

    Returns
    -------
    str
        The DIAGNOSER_AGENT_ID to store in .env
    """
    print("=" * 60)
    print("  SRE Flight Crew — Diagnoser Agent Deployment")
    print("=" * 60)
    print()
    print("  FOUNDRY SETUP CHECKLIST:")
    print("  1. Verify you have created an Azure AI Search service:")
    print("     - Standard search service (for scalability and performance)")
    print("     - Search units: 1/1 (est. cost $0.00 on free plan)")
    print("     - Replicas: 1 or 2 (depending on read SLA preference)")
    print("     - Partitions: 1 (50 MB Storage limit)")
    print("  2. Verify Azure AI Search is linked to your Azure AI Foundry project.")
    print("  3. Make sure you are authenticated locally via 'az login'.")
    print("=" * 60)
    print()

    if not AZURE_PROJECT_ENDPOINT:
        print("ERROR: AZURE_PROJECT_ENDPOINT not set in .env")
        sys.exit(1)

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=AZURE_PROJECT_ENDPOINT,
        credential=credential,
    )

    # Get an authenticated AsyncOpenAI client from the Foundry project
    openai_client = project_client.get_openai_client()

    try:
        # ── Step 1: Upload runbook files ─────────────────────────────────
        print("[1/3] Uploading runbook files to Foundry...")
        kb_path = Path(KNOWLEDGE_BASE_DIR)
        file_ids = []

        for md_file in sorted(kb_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8").strip()
            if not content:
                print(f"  ⚠  Skipping empty file: {md_file.name}")
                continue

            with open(md_file, "rb") as f:
                uploaded = await openai_client.files.create(
                    file=f,
                    purpose="assistants",
                )
            file_ids.append(uploaded.id)
            print(f"  ✓ Uploaded: {md_file.name} → {uploaded.id}")

        if not file_ids:
            print("ERROR: No runbook files found in", kb_path)
            sys.exit(1)

        print(f"\n  Total files uploaded: {len(file_ids)}")

        # ── Step 2: Create vector store ──────────────────────────────────
        print("\n[2/3] Creating vector store for runbooks...")
        vector_store = await openai_client.vector_stores.create(
            name="SRE Flight Crew — Runbooks",
            file_ids=file_ids,
        )
        print(f"  ✓ Vector store created: {vector_store.id}")

        # ── Step 3: Create the Diagnoser assistant ───────────────────────
        print(f"\n[3/3] Creating Diagnoser agent (model={MODEL_DEPLOYMENT_NAME})...")

        agent = await openai_client.beta.assistants.create(
            model=MODEL_DEPLOYMENT_NAME,
            name="SRE-Diagnoser",
            instructions=DIAGNOSER_AGENT_INSTRUCTIONS,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id],
                }
            },
            temperature=0.2,  # Low temp for deterministic reasoning
            response_format={"type": "json_object"},
        )

        print(f"  ✓ Agent created: {agent.id}")
        print(f"  Name: {agent.name}")
        print(f"  Model: {agent.model}")

        # ── Done ─────────────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("  DEPLOYMENT COMPLETE")
        print("=" * 60)
        print()
        print("  Add this to your .env file:")
        print()
        print(f"  DIAGNOSER_AGENT_ID={agent.id}")
        print()
        print("=" * 60)

        return agent.id

    finally:
        await openai_client.close()
        await project_client.close()
        await credential.close()


async def update_diagnoser_agent(agent_id: str) -> None:
    """
    Update an existing Diagnoser agent's instructions and file search.

    Use this when you've changed the prompt_templates or runbook files
    and want to update the deployed agent without creating a new one.

    Parameters
    ----------
    agent_id : str
        The existing DIAGNOSER_AGENT_ID from .env
    """
    print(f"Updating agent {agent_id}...")

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=AZURE_PROJECT_ENDPOINT,
        credential=credential,
    )
    openai_client = project_client.get_openai_client()

    try:
        # Upload new files
        kb_path = Path(KNOWLEDGE_BASE_DIR)
        file_ids = []
        for md_file in sorted(kb_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8").strip()
            if not content:
                continue
            with open(md_file, "rb") as f:
                uploaded = await openai_client.files.create(
                    file=f,
                    purpose="assistants",
                )
            file_ids.append(uploaded.id)
            print(f"  ✓ Uploaded: {md_file.name}")

        # Create new vector store
        vector_store = await openai_client.vector_stores.create(
            name="SRE Flight Crew — Runbooks (updated)",
            file_ids=file_ids,
        )
        print(f"  ✓ Vector store: {vector_store.id}")

        # Update agent
        await openai_client.beta.assistants.update(
            assistant_id=agent_id,
            instructions=DIAGNOSER_AGENT_INSTRUCTIONS,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id],
                }
            },
        )
        print(f"  ✓ Agent {agent_id} updated successfully")

    finally:
        await openai_client.close()
        await project_client.close()
        await credential.close()


# ─── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        # Update existing agent
        from shared.config import DIAGNOSER_AGENT_ID
        if not DIAGNOSER_AGENT_ID or DIAGNOSER_AGENT_ID == "your-agent-id-here":
            print("ERROR: DIAGNOSER_AGENT_ID not set — nothing to update")
            sys.exit(1)
        asyncio.run(update_diagnoser_agent(DIAGNOSER_AGENT_ID))
    else:
        # Create new agent
        asyncio.run(deploy_diagnoser_agent())
