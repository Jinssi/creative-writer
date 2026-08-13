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

from agent_framework_client import cw_name, get_credential


def _empty_research() -> str:
    return json.dumps({"web": [], "entities": [], "news": []})


def _extract_assistant(messages):
    """Return ``(text, citations)`` from the assistant messages.

    ``citations`` come from the Bing grounding URL annotations (authoritative real
    URLs) via the SDK's ``url_citation_annotations`` helper, which is far more
    reliable than trusting the model to hand-format JSON links. ``text`` is the
    model's prose (used only for descriptions).
    """
    last_text = ""
    citations = []
    seen = set()
    for m in messages:
        role = getattr(m, "role", None)
        role = getattr(role, "value", role)  # enum or str
        role = str(role).lower() if role is not None else ""
        if role and role not in ("assistant", "agent"):
            continue
        # Latest assistant text via the SDK helper (falls back to raw content).
        for tm in getattr(m, "text_messages", None) or []:
            value = getattr(getattr(tm, "text", None), "value", None)
            if value:
                last_text = value
        for ann in getattr(m, "url_citation_annotations", None) or []:
            citation = getattr(ann, "url_citation", None)
            url = getattr(citation, "url", None) if citation is not None else None
            if not url or url in seen:
                continue
            seen.add(url)
            citations.append({"url": url, "name": getattr(citation, "title", None) or url, "description": ""})
    return last_text, citations


def _parse_json_object(text: str) -> dict:
    text = (text or "").strip()
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
    return parsed if isinstance(parsed, dict) else {}


@trace
def research_topic(
    query: Annotated[str, "The research question or topic to investigate on the web."],
) -> str:
    """Search the web with Bing grounding and return structured findings as JSON.

    Returns a JSON string of the form ``{"web": [{"url","name","description"}], ...}``.
    Never raises: on any failure it returns an empty result set.
    """
    try:
        from azure.ai.agents import AgentsClient
        from azure.ai.agents.models import BingGroundingTool, ListSortOrder
        from azure.ai.projects import AIProjectClient

        endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
        # The Bing-grounding agent runtime supports a narrower set of models than
        # plain chat completions; default to a broadly-supported model and allow override.
        deployment = os.getenv("AZURE_GROUNDING_DEPLOYMENT_NAME", "gpt-5-mini")
        connection_name = os.getenv("BING_CONNECTION_NAME", "bing-connection")
        credential = get_credential()

        # The Bing grounding connection id lives on the project; agent CRUD lives on
        # AgentsClient (AIProjectClient.agents is an operations group without create_agent).
        with AIProjectClient(endpoint=endpoint, credential=credential) as project:
            connection_id = project.connections.get(name=connection_name).id
        bing = BingGroundingTool(connection_id=connection_id)

        with AgentsClient(endpoint=endpoint, credential=credential) as agents_client:
            agent = agents_client.create_agent(
                model=deployment,
                name=cw_name("researcher-bing"),
                instructions=(
                    "You are a web researcher. Use the Bing tool to find 4-6 authoritative, "
                    "recent sources that directly answer the query, and cite each source you "
                    "use. Then return ONLY a JSON object shaped as "
                    '{"web": [{"url": "", "name": "", "description": ""}], "entities": [], "news": []}. '
                    "Each description is 1-2 sentences summarizing what that source says about "
                    "the query. No code fences, no prose outside the JSON."
                ),
                tools=bing.definitions,
            )
            try:
                response, citations = "", []
                for attempt in range(2):  # one retry for transient grounding failures
                    thread = agents_client.threads.create()
                    agents_client.messages.create(thread_id=thread.id, role="user", content=query)
                    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                    if getattr(run, "status", None) == "failed":
                        print(f"research_topic run failed (attempt {attempt + 1}): {getattr(run, 'last_error', None)}")
                        continue
                    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
                    response, citations = _extract_assistant(messages)
                    break
            finally:
                try:
                    agents_client.delete_agent(agent.id)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001 - research is best-effort
        print(f"research_topic failed: {exc}")
        return _empty_research()

    parsed = _parse_json_object(response)
    model_web = parsed.get("web") if isinstance(parsed.get("web"), list) else []

    # Prefer real grounding citations; enrich them with the model's descriptions.
    if citations:
        desc_by_url = {
            item["url"]: item.get("description", "")
            for item in model_web
            if isinstance(item, dict) and item.get("url")
        }
        for c in citations:
            c["description"] = desc_by_url.get(c["url"], "")
        web = citations
    else:
        web = model_web

    # Normalize so downstream (writer template, fact-checker) always gets the same shape.
    normalized = []
    for item in web:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        name = item.get("name") or item.get("title") or url
        normalized.append({"url": url, "name": name, "title": name, "description": item.get("description", "")})

    return json.dumps(
        {
            "web": normalized,
            "entities": parsed.get("entities", []) if isinstance(parsed.get("entities"), list) else [],
            "news": parsed.get("news", []) if isinstance(parsed.get("news"), list) else [],
        }
    )


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
