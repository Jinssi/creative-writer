"""Automated AI red teaming for the Creative Writer agents (Preview).

Uses the Azure AI Evaluation red-team agent to probe the content-generation path
with adversarial prompts across safety risk categories and attack strategies. Run
ad hoc, or on a schedule via ``.github/workflows/scheduled-evaluation.yml``.

Docs: https://learn.microsoft.com/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent
"""
import asyncio
import os

from azure.identity import DefaultAzureCredential
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy


def _credential() -> DefaultAzureCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


async def _writer_target(query: str) -> str:
    """Target callback: send an adversarial prompt through the writer agent."""
    from agent_framework_client import build_agent

    writer = build_agent(
        "writer",
        "You are an expert copywriter for Contoso Outdoors. Follow the brief exactly.",
    )
    result = await writer.run(query)
    return getattr(result, "text", str(result))


async def run_red_team(scan_name: str = "creative-writer-red-team", num_objectives: int = 5):
    red_team = RedTeam(
        azure_ai_project=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        credential=_credential(),
        risk_categories=[
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=num_objectives,
    )

    result = await red_team.scan(
        target=_writer_target,
        scan_name=scan_name,
        attack_strategies=[
            AttackStrategy.Baseline,
            AttackStrategy.Flip,
            AttackStrategy.Base64,
            AttackStrategy.Jailbreak,
        ],
    )
    print(f"Red-team scan '{scan_name}' complete. Results uploaded to the Foundry project.")
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(run_red_team())
