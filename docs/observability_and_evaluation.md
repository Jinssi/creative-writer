# Observability & Evaluation

This app was modernized to the **current-generation Foundry experience** and the
**Microsoft Agent Framework**. This page summarizes the AI operations features and
how they map to code in this repo.

| Capability | Status | Where it lives |
| --- | --- | --- |
| Multi-agent orchestration | GA | [`src/api/orchestrator.py`](../src/api/orchestrator.py), [`src/api/agent_framework_client.py`](../src/api/agent_framework_client.py) |
| Tracing (OpenTelemetry → App Insights) | GA | [`src/api/telemetry.py`](../src/api/telemetry.py) |
| Evaluation (quality + safety + task completion + tool-call accuracy) | GA | [`src/api/evaluate/evaluators.py`](../src/api/evaluate/evaluators.py), [`src/api/evaluate/agent_evaluation.py`](../src/api/evaluate/agent_evaluation.py) |
| Continuous evaluation | Preview | [`src/api/evaluate/continuous_evaluation.py`](../src/api/evaluate/continuous_evaluation.py) |
| Scheduled evaluation & red teaming | Preview | [`src/api/evaluate/red_team.py`](../src/api/evaluate/red_team.py), [`.github/workflows/scheduled-evaluation.yml`](../.github/workflows/scheduled-evaluation.yml) |
| Agent Monitor dashboard | Preview | Foundry portal (see below) |
| Prompt optimization | Playground + evals | See below |

## Multi-agent orchestration (Microsoft Agent Framework)

The four-agent workflow — **researcher → product marketing → writer → editor**
(with an editor feedback loop) — is preserved but now runs on the Microsoft Agent
Framework, the designated successor to AutoGen and Semantic Kernel.

- The **researcher** and **product** agents call function tools
  ([`src/api/agents/tools.py`](../src/api/agents/tools.py)) for Bing grounding and
  Azure AI Search vector retrieval, so their tool calls are traced and can be
  scored for tool-call accuracy.
- The **writer** and **editor** agents reuse the original Prompty templates as
  their prompts, keeping the app's carefully tuned intent.

## Tracing (GA)

`setup_telemetry()` exports OpenTelemetry spans (agents, tools, and model calls)
to the Application Insights resource attached to the Foundry project. Set
`LOCAL_TRACING_ENABLED=true` to trace to the console + Prompty `.runs` locally
instead. In Azure, traces appear under the project's **Tracing** and **Agent
Monitor** views.

## Evaluation (GA)

Two complementary evaluator sets:

- **Article quality/safety** (`ArticleEvaluator`): relevance, coherence, fluency,
  groundedness, **task adherence** (task completion), plus the content-safety
  evaluators (violence, hate/unfairness, self-harm, sexual) and friendliness.
- **Agent run** (`agent_evaluation.py`): intent resolution, task adherence, and
  **tool-call accuracy**, computed from the agents' messages, tool definitions,
  and tool calls.

## Continuous evaluation (Preview)

`continuous_evaluation.py` registers sampling of **live** agent responses (default
20%) and scores them with the agent evaluators. Results flow to Application
Insights and the Agent Monitor dashboard. Run once to register:

```bash
cd src/api
python -m evaluate.continuous_evaluation
```

## Scheduled evaluation & red teaming (Preview)

`red_team.py` runs the Azure AI red-teaming agent against the content-generation
path across safety risk categories and attack strategies (baseline, flip, base64,
jailbreak). The [`scheduled-evaluation.yml`](../.github/workflows/scheduled-evaluation.yml)
workflow runs the batch evaluation and a red-team scan on a daily cron and on
demand.

```bash
cd src/api
python -m evaluate.red_team
```

## Agent Monitor dashboard (Preview)

The **Agent Monitor** dashboard in the Foundry portal visualizes the traces and
continuous-evaluation scores emitted above (latency, tool usage, quality/safety
trends). No code is required — open your project → **Observability / Agent
Monitor**. It reads from the same Application Insights resource configured for
tracing.

## Prompt optimization

There is no standalone "Prompt Optimizer" in the current Foundry experience.
The supported loop is **playground iteration + evaluations**:

1. Iterate a prompt in the Foundry playground against the model deployment.
2. Run the batch evaluators here (`python -m evaluate.evaluate`) to score changes.
3. Compare runs in the Foundry **Evaluation** view and keep the best prompt.

The Prompty templates in `src/api/agents/**/*.prompty` are the source of truth for
each agent's prompt, so playground-tuned prompts can be copied straight back in.
