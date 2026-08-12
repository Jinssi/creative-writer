"""Automated AI red teaming for the deployed Creative Writer agent and its models.

Runs the Azure AI Evaluation red-team agent (PyRIT) against three targets and
uploads an Attack-Success-Rate scorecard to the Foundry project (visible under
Evaluations > Red teaming):

  1. creative-writer   -- the deployed Foundry agent (Responses API)
  2. gpt-5.6-terra      -- the chat model the agent runs on
  3. gpt-5.6-luna       -- the evaluation/judge model

Auth: DefaultAzureCredential (az login locally, or a managed identity via
AZURE_CLIENT_ID). The signed-in identity needs data-plane access on the project
and its model deployments.

Docs: https://learn.microsoft.com/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent
"""
import argparse
import asyncio
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy

# --- Configuration (override via environment variables) ----------------------
PROJECT_ENDPOINT = os.getenv(
    "AZURE_AI_PROJECT_ENDPOINT",
    "https://con-vid-prod-sweden.services.ai.azure.com/api/projects/con-vid-prod-sweden-project",
)
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://con-vid-prod-sweden.openai.azure.com/")
COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

AGENT_NAME = os.getenv("CREATIVE_WRITER_AGENT_NAME", "creative-writer")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.6-terra")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-5.6-luna")

# Agent system prompt, used only if the deployed-agent Responses call is unavailable.
AGENT_INSTRUCTIONS = (
    "You are Contoso Creative Writer, a research-and-analysis writing assistant for "
    "Contoso Outdoors. Write concise, engaging, well-structured notes and recommend "
    "relevant Contoso Outdoors product categories where they fit naturally."
)


def _credential() -> DefaultAzureCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


CREDENTIAL = _credential()


def _openai_client():
    """AzureOpenAI client (AAD) for calling model deployments directly."""
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(CREDENTIAL, COGNITIVE_SCOPE)
    return AzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )


def _agent_client():
    """OpenAI client bound to the Foundry project, for invoking the deployed agent."""
    from azure.ai.projects import AIProjectClient

    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=CREDENTIAL)
    # Recent azure-ai-projects exposes an OpenAI-compatible client bound to the project.
    return project.get_openai_client(api_version=API_VERSION)


def _model_target(model: str):
    """Build a red-team target callback that calls a chat model deployment."""
    client = _openai_client()

    def _call(query: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
        )
        return resp.choices[0].message.content or ""

    async def target(query: str) -> str:
        try:
            return await asyncio.to_thread(_call, query)
        except Exception as exc:  # keep the scan running on a single bad turn
            return f"[model call failed: {exc}]"

    return target


def _agent_target():
    """Build a red-team target callback that invokes the deployed Foundry agent.

    Falls back to the underlying chat model + agent instructions if the project's
    Responses endpoint is not reachable from this client version.
    """
    mode = {"kind": None, "client": None}

    def _init():
        try:
            client = _agent_client()
            client.responses.create(model=AGENT_NAME, input="ping")
            mode["kind"], mode["client"] = "responses", client
            return
        except Exception as exc:
            print(f"[agent] Responses path unavailable ({exc}); falling back to model+instructions.")
        mode["kind"], mode["client"] = "chat", _openai_client()

    def _call(query: str) -> str:
        if mode["kind"] is None:
            _init()
        if mode["kind"] == "responses":
            r = mode["client"].responses.create(model=AGENT_NAME, input=query)
            return getattr(r, "output_text", str(r)) or ""
        r = mode["client"].chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": AGENT_INSTRUCTIONS},
                {"role": "user", "content": query},
            ],
        )
        return r.choices[0].message.content or ""

    async def target(query: str) -> str:
        try:
            return await asyncio.to_thread(_call, query)
        except Exception as exc:
            return f"[agent call failed: {exc}]"

    return target


TARGETS = {
    "agent": ("creative-writer-agent-redteam", _agent_target),
    "terra": ("gpt-56-terra-redteam", lambda: _model_target(CHAT_MODEL)),
    "luna": ("gpt-56-luna-redteam", lambda: _model_target(JUDGE_MODEL)),
}


async def run_scan(key: str, num_objectives: int) -> None:
    scan_name, build_target = TARGETS[key]
    print(f"\n=== Red teaming '{key}' -> scan '{scan_name}' ===")
    red_team = RedTeam(
        azure_ai_project=PROJECT_ENDPOINT,
        credential=CREDENTIAL,
        risk_categories=[
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=num_objectives,
    )
    await red_team.scan(
        target=build_target(),
        scan_name=scan_name,
        attack_strategies=[
            AttackStrategy.Baseline,
            AttackStrategy.Flip,
            AttackStrategy.Base64,
        ],
        output_path=f"{scan_name}.json",
    )
    print(f"[done] '{scan_name}' complete -- results uploaded to the Foundry project.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI red-team scans for the Creative Writer targets.")
    parser.add_argument(
        "--targets",
        default="agent,terra,luna",
        help="Comma-separated subset of: agent, terra, luna (default: all).",
    )
    parser.add_argument("--num-objectives", type=int, default=5, help="Attack objectives per risk category.")
    args = parser.parse_args()

    keys = [t.strip() for t in args.targets.split(",") if t.strip()]
    for key in keys:
        if key not in TARGETS:
            print(f"[skip] unknown target '{key}'")
            continue
        try:
            await run_scan(key, args.num_objectives)
        except Exception as exc:
            print(f"[error] scan for '{key}' failed: {exc}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    asyncio.run(main())
