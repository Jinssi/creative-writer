"""Function tools exposed to the Agent Framework agents.

These wrap the app's capabilities (Bing web grounding + optional reference
retrieval) as callable tools. Both degrade gracefully: if grounding or the
reference catalog is unavailable, the tool returns an empty result so article
generation never breaks.
"""
import json
import os
from typing import Annotated

from prompty.tracer import trace

from agent_framework_client import get_credential


def _empty_research() -> str:
    return json.dumps({"web": [], "entities": [], "news": []})


def _extract_assistant_text(messages) -> str:
    """Return the text of the most relevant assistant message, robust to SDK ordering."""
    assistant_texts = []
    for m in messages:
        role = getattr(m, "role", None)
        role = getattr(role, "value", role)  # enum or str
        if role and str(role).lower() != "assistant":
            continue
        content = getattr(m, "content", None) or []
        for item in content:
            text = getattr(item, "text", None)
            value = getattr(text, "value", None) if text is not None else None
            if value:
                assistant_texts.append(value)
    # Prefer the last assistant message (final answer).
    return assistant_texts[-1] if assistant_texts else ""


@trace
def research_topic(
    query: Annotated[str, "The research question or topic to investigate on the web."],
) -> str:
    """Search the web with Bing grounding and return structured findings as JSON.

    Returns a JSON string of the form ``{"web": [{"url","name","description"}], ...}``.
    Never raises: on any failure it returns an empty result set.
    """
    try:
        from azure.ai.agents.models import BingGroundingTool
        from azure.ai.projects import AIProjectClient

        endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.6-terra")
        connection_name = os.getenv("BING_CONNECTION_NAME", "bing-connection")

        with AIProjectClient(endpoint=endpoint, credential=get_credential()) as project:
            bing_connection = project.connections.get(name=connection_name)
            bing = BingGroundingTool(connection_id=bing_connection.id)

            agent = project.agents.create_agent(
                model=deployment,
                name="researcher-bing",
                instructions=(
                    "You are a web researcher. Use Bing to find 4-6 authoritative, recent "
                    "sources for the query. Return ONLY a JSON object shaped as "
                    '{"web": [{"url": "", "name": "", "description": ""}], "entities": [], "news": []}. '
                    "Each description should be 1-2 sentences summarizing what the source says "
                    "about the query. No code fences, no prose outside the JSON."
                ),
                tools=bing.definitions,
            )
            try:
                thread = project.agents.threads.create()
                project.agents.messages.create(thread_id=thread.id, role="user", content=query)
                run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                if getattr(run, "status", None) == "failed":
                    print(f"research_topic run failed: {getattr(run, 'last_error', None)}")
                    return _empty_research()
                messages = project.agents.messages.list(thread_id=thread.id)
                response = _extract_assistant_text(messages)
            finally:
                try:
                    project.agents.delete_agent(agent.id)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001 - research is best-effort
        print(f"research_topic failed: {exc}")
        return _empty_research()

    text = (response or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        try:
            parsed = json.loads(text[start : end + 1]) if start != -1 and end != -1 else {}
        except json.JSONDecodeError:
            parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    parsed.setdefault("web", [])
    parsed.setdefault("entities", [])
    parsed.setdefault("news", [])
    return json.dumps(parsed)


@trace
def search_products(
    context: Annotated[str, "A description of the references/examples to find for the article."],
) -> str:
    """Retrieve reference items from the catalog (if configured) as a JSON array.

    Optional and generic: if no reference catalog is configured or the search
    fails, returns an empty array so the writer proceeds with research alone.
    """
    if not os.getenv("AZURE_SEARCH_ENDPOINT"):
        return json.dumps([])
    try:
        from agents.product import product as product_agent

        products = product_agent.find_products(context)
        return json.dumps(products or [])
    except Exception as exc:  # noqa: BLE001 - references are optional
        print(f"search_products unavailable, continuing without references: {exc}")
        return json.dumps([])
