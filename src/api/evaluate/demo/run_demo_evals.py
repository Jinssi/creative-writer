"""Run the full evaluation suite and upload results to the Foundry project.

Produces Foundry Evaluation runs covering the demo's control criteria:
  - Quality:        relevance, coherence, fluency, groundedness
  - Task completion: task adherence, intent resolution
  - Safety:         violence, hate/unfairness, self-harm, sexual
  - Tool-call accuracy (agent runs)

Results upload to the Foundry project and print a Studio URL for the demo.

Usage (from src/api):
    python -m evaluate.demo.run_demo_evals
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()
# Local runs authenticate via `az login`, not the deployed managed identity.
os.environ.pop("AZURE_CLIENT_ID", None)

from azure.identity import DefaultAzureCredential  # noqa: E402
from azure.ai.evaluation import evaluate  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _cred():
    return DefaultAzureCredential()


def _project():
    return os.environ["AZURE_AI_PROJECT_ENDPOINT"]


def _model_config():
    return {
        "azure_deployment": os.getenv("AZURE_OPENAI_4_EVAL_DEPLOYMENT_NAME", "gpt-5.6-luna"),
        "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
    }


def run_article_eval():
    from azure.ai.evaluation import (
        RelevanceEvaluator, CoherenceEvaluator, FluencyEvaluator, GroundednessEvaluator,
        TaskAdherenceEvaluator, IntentResolutionEvaluator,
        ViolenceEvaluator, HateUnfairnessEvaluator, SelfHarmEvaluator, SexualEvaluator,
    )

    mc = _model_config()
    proj = _project()
    c = _cred()

    evaluators = {
        "relevance": RelevanceEvaluator(mc),
        "coherence": CoherenceEvaluator(mc),
        "fluency": FluencyEvaluator(mc),
        "groundedness": GroundednessEvaluator(mc),
        "task_adherence": TaskAdherenceEvaluator(mc),
        "intent_resolution": IntentResolutionEvaluator(mc),
        "violence": ViolenceEvaluator(azure_ai_project=proj, credential=c),
        "hate_unfairness": HateUnfairnessEvaluator(azure_ai_project=proj, credential=c),
        "self_harm": SelfHarmEvaluator(azure_ai_project=proj, credential=c),
        "sexual": SexualEvaluator(azure_ai_project=proj, credential=c),
    }

    qcr = {"query": "${data.query}", "response": "${data.response}", "context": "${data.context}"}
    qr = {"query": "${data.query}", "response": "${data.response}"}
    evaluator_config = {
        "relevance": {"column_mapping": qcr},
        "coherence": {"column_mapping": qr},
        "fluency": {"column_mapping": qr},
        "groundedness": {"column_mapping": qcr},
        "task_adherence": {"column_mapping": qr},
        "intent_resolution": {"column_mapping": qr},
        "violence": {"column_mapping": qr},
        "hate_unfairness": {"column_mapping": qr},
        "self_harm": {"column_mapping": qr},
        "sexual": {"column_mapping": qr},
    }

    result = evaluate(
        evaluation_name="creative-writer-article-quality-safety",
        data=os.path.join(HERE, "article_eval.jsonl"),
        evaluators=evaluators,
        evaluator_config=evaluator_config,
        azure_ai_project=proj,
    )
    print("\n=== Article quality + safety + task completion ===")
    print("Studio URL:", result.get("studio_url"))
    print("Metrics:", result.get("metrics"))
    return result


def run_tool_eval():
    from azure.ai.evaluation import ToolCallAccuracyEvaluator

    mc = _model_config()
    proj = _project()

    evaluators = {"tool_call_accuracy": ToolCallAccuracyEvaluator(model_config=mc)}
    evaluator_config = {
        "tool_call_accuracy": {
            "column_mapping": {
                "query": "${data.query}",
                "tool_calls": "${data.tool_calls}",
                "tool_definitions": "${data.tool_definitions}",
            }
        }
    }

    result = evaluate(
        evaluation_name="creative-writer-tool-call-accuracy",
        data=os.path.join(HERE, "agent_tool_eval.jsonl"),
        evaluators=evaluators,
        evaluator_config=evaluator_config,
        azure_ai_project=proj,
    )
    print("\n=== Tool-call accuracy ===")
    print("Studio URL:", result.get("studio_url"))
    print("Metrics:", result.get("metrics"))
    return result


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "article"):
        try:
            run_article_eval()
        except Exception as exc:  # noqa: BLE001
            print(f"Article eval failed: {exc}")
    if which in ("all", "tool"):
        try:
            run_tool_eval()
        except Exception as exc:  # noqa: BLE001
            print(f"Tool-call eval failed: {exc}")


if __name__ == "__main__":
    main()
