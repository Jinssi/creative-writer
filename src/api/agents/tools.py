"""Function tools exposed to the Agent Framework agents.

These wrap the app's capabilities (keyless web search + optional reference
retrieval) as callable tools. Both degrade gracefully: if search or the
reference catalog is unavailable, the tool returns an empty result so article
generation never breaks.
"""
import json
import os
from typing import Annotated

from prompty.tracer import trace


def _empty_research() -> str:
    return json.dumps({"web": [], "entities": [], "news": []})


@trace
def research_topic(
    query: Annotated[str, "The research question or topic to investigate on the web."],
) -> str:
    """Search the web (keyless DuckDuckGo) and return structured findings as JSON.

    Returns a JSON string of the form ``{"web": [{"url","name","title","description"}], ...}``.
    Never raises: on any failure it returns an empty result set. This avoids any
    dependency on an Azure Bing-grounding connection.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:  # older package name
            from duckduckgo_search import DDGS

        max_results = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "6"))
        web = []
        seen = set()
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=max_results):
                url = r.get("href") or r.get("url") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                title = r.get("title") or url
                web.append(
                    {"url": url, "name": title, "title": title, "description": r.get("body") or ""}
                )
        return json.dumps({"web": web, "entities": [], "news": []})
    except Exception as exc:  # noqa: BLE001 - research is best-effort
        print(f"research_topic failed: {exc}")
        return _empty_research()


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
