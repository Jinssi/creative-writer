"""Agent-focused evaluators: task completion and tool-call accuracy.

These complement the article-quality evaluators in ``evaluators.py``. They operate
on agent *runs* (the messages, tool definitions and tool calls produced by the
Agent Framework agents) rather than on the final article text, so they can score
whether the agent resolved the user's intent, adhered to the task, and called its
tools correctly.

Docs: https://learn.microsoft.com/azure/ai-foundry/how-to/develop/agent-evaluate-sdk
"""
import os

from azure.ai.evaluation import (
    IntentResolutionEvaluator,
    TaskAdherenceEvaluator,
    ToolCallAccuracyEvaluator,
)


def _model_config() -> dict:
    return {
        "azure_deployment": os.environ.get("AZURE_OPENAI_4_EVAL_DEPLOYMENT_NAME", "gpt-5.6-luna"),
        "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        "azure_endpoint": os.environ.get(
            "AZURE_OPENAI_ENDPOINT",
            f"https://{os.getenv('AZURE_OPENAI_NAME')}.services.ai.azure.com/",
        ),
    }


def build_agent_evaluators() -> dict:
    """Return the GA agent evaluators used for both batch and continuous evaluation."""
    model_config = _model_config()
    return {
        "intent_resolution": IntentResolutionEvaluator(model_config=model_config),
        "task_adherence": TaskAdherenceEvaluator(model_config=model_config),
        "tool_call_accuracy": ToolCallAccuracyEvaluator(model_config=model_config),
    }


def evaluate_agent_run(query, response, tool_calls=None, tool_definitions=None) -> dict:
    """Evaluate a single agent run for intent resolution, task adherence and tool-call accuracy.

    ``query``/``response`` may be strings or the message lists produced by an agent run.
    ``tool_calls`` and ``tool_definitions`` enable tool-call-accuracy scoring.
    """
    evaluators = build_agent_evaluators()
    results = {}

    results["intent_resolution"] = evaluators["intent_resolution"](query=query, response=response)
    results["task_adherence"] = evaluators["task_adherence"](query=query, response=response)

    if tool_calls is not None and tool_definitions is not None:
        results["tool_call_accuracy"] = evaluators["tool_call_accuracy"](
            query=query,
            response=response,
            tool_calls=tool_calls,
            tool_definitions=tool_definitions,
        )

    return results
