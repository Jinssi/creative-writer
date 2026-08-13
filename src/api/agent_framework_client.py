"""Central Microsoft Agent Framework wiring for Contoso Creative Writer.

This module is the single place that knows how to authenticate to the shared
Foundry project and how to construct agents. Keeping it isolated means that if
the Agent Framework surface shifts, only this file needs to change.
"""
import os
from functools import lru_cache
from pathlib import Path

from azure.identity import DefaultAzureCredential
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

# ---- Agent naming convention (see docs/agent-naming.md) ----
# Every agent that belongs to the Creative Writer workload carries the "-CW"
# suffix so it is instantly identifiable in the shared Foundry project, in
# traces, and in monitoring. Use cw_name() (or build_agent, which applies it
# automatically) whenever you name an agent for this app.
WORKLOAD_SUFFIX = "CW"


def cw_name(role: str) -> str:
    """Return the workload-qualified agent name, e.g. ``researcher`` -> ``researcher-CW``."""
    role = role.strip()
    return role if role.endswith(f"-{WORKLOAD_SUFFIX}") else f"{role}-{WORKLOAD_SUFFIX}"


def get_credential() -> DefaultAzureCredential:
    """DefaultAzureCredential, pinned to the shared managed identity when deployed.

    Locally this falls back to ``az login``; in Azure it uses the user-assigned
    managed identity referenced by ``AZURE_CLIENT_ID``.
    """
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


def _project_endpoint() -> str:
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Point it at your Foundry "
            "project, e.g. https://<account>.services.ai.azure.com/api/projects/<project>."
        )
    return endpoint


def chat_client(model: str | None = None) -> FoundryChatClient:
    """Create a Foundry chat client bound to a model deployment."""
    return FoundryChatClient(
        project_endpoint=_project_endpoint(),
        model=model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.6-terra"),
        credential=get_credential(),
    )


def build_agent(
    name: str,
    instructions: str,
    *,
    description: str | None = None,
    tools: list | None = None,
    model: str | None = None,
) -> Agent:
    """Construct an Agent Framework agent on the shared Foundry project.

    The agent name is automatically qualified with the ``-CW`` workload suffix.
    """
    return Agent(
        client=chat_client(model),
        name=cw_name(name),
        instructions=instructions,
        description=description,
        tools=tools or [],
    )


@lru_cache(maxsize=None)
def prompty_instructions(prompty_path: str) -> str:
    """Return the system body of a ``.prompty`` file to reuse as agent instructions.

    This preserves the original, carefully tuned prompts (the app's intent) while
    letting the Agent Framework own execution and orchestration.
    """
    text = Path(prompty_path).read_text(encoding="utf-8")
    parts = text.split("---")
    body = parts[2] if len(parts) >= 3 else text
    return body.replace("system:", "", 1).strip()
