"""Continuous evaluation of live agent responses (Preview).

Continuous evaluation samples real agent runs as they happen and scores a subset
with the same agent evaluators used for batch runs (intent resolution, task
adherence, tool-call accuracy). Results are emitted to Application Insights and
surface in the Agent Monitor dashboard.

This is a Preview capability; the sampling/redaction configuration below reflects
the ``azure-ai-projects`` continuous agent-evaluation API. Run once to register
the schedule against your Foundry project.
"""
import os

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def _credential() -> DefaultAzureCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


def enable_continuous_evaluation(sampling_percent: int = 20, max_request_rate: int = 100) -> None:
    """Register continuous agent evaluation on the Foundry project.

    Args:
        sampling_percent: Percentage of live agent runs to evaluate.
        max_request_rate: Upper bound on evaluation requests per hour.
    """
    from azure.ai.projects.models import (
        AgentEvaluationRequest,
        AgentEvaluationSamplingConfiguration,
        AgentEvaluationRedactionConfiguration,
        EvaluatorConfiguration,
        EvaluatorIds,
    )

    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    app_insights_conn = os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
    eval_deployment = os.getenv("AZURE_OPENAI_4_EVAL_DEPLOYMENT_NAME", "gpt-5.6-luna")

    evaluators = {
        "intent_resolution": EvaluatorConfiguration(id=EvaluatorIds.INTENT_RESOLUTION.value),
        "task_adherence": EvaluatorConfiguration(id=EvaluatorIds.TASK_ADHERENCE.value),
        "tool_call_accuracy": EvaluatorConfiguration(id=EvaluatorIds.TOOL_CALL_ACCURACY.value),
    }
    # Judge model for AI-assisted evaluators.
    for cfg in evaluators.values():
        cfg.init_params = {"deployment_name": eval_deployment}

    with AIProjectClient(endpoint=endpoint, credential=_credential()) as project:
        project.evaluations.create_agent_evaluation(
            evaluation=AgentEvaluationRequest(
                app_insights_connection_string=app_insights_conn,
                evaluators=evaluators,
                sampling_configuration=AgentEvaluationSamplingConfiguration(
                    name="creative-writer-continuous",
                    sampling_percent=sampling_percent,
                    max_request_rate=max_request_rate,
                ),
                redaction_configuration=AgentEvaluationRedactionConfiguration(
                    redact_score_properties=False,
                ),
            )
        )
    print(
        f"Continuous evaluation registered: sampling {sampling_percent}% of live agent runs "
        f"with intent_resolution, task_adherence, tool_call_accuracy."
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    enable_continuous_evaluation()
