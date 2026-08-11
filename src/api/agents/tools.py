"""Function tools exposed to the Agent Framework agents.

These wrap the app's existing capabilities (Bing grounding + Azure AI Search
vector retrieval) as callable tools so the agents genuinely invoke them. That
also makes tool-call-accuracy evaluation meaningful.
"""
import json
import os
from typing import Annotated

from azure.ai.agents.models import BingGroundingTool
from azure.ai.projects import AIProjectClient
from prompty.tracer import trace

from agent_framework_client import get_credential

# Reuse the existing, unchanged product retrieval (embeddings + AI Search).
from agents.product import product as product_agent


@trace
def research_topic(
    query: Annotated[str, "The research question or topic to investigate on the web."],
) -> str:
    """Search the web with Bing grounding and return structured findings as JSON.

    Returns a JSON string of the form ``{"web": [{"url","name","description"}], ...}``.
    """
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
                "You are a web researcher. Use Bing to find 3-5 authoritative, recent "
                "sources for the query and return ONLY a JSON object shaped as "
                '{"web": [{"url": "", "name": "", "description": ""}], "entities": [], "news": []}. '
                "Do not include code fences or any prose outside the JSON."
            ),
            tools=bing.definitions,
        )
        try:
            thread = project.agents.threads.create()
            project.agents.messages.create(thread_id=thread.id, role="user", content=query)
            project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

            messages = project.agents.messages.list(thread_id=thread.id)
            response = messages[0].content[0].text.value
        finally:
            project.agents.delete_agent(agent.id)

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        parsed = {"web": [], "entities": [], "news": []}
    parsed.setdefault("entities", [])
    parsed.setdefault("news", [])
    return json.dumps(parsed)


@trace
def search_products(
    context: Annotated[str, "A description of the products to find, e.g. 'tents and sleeping bags'."],
) -> str:
    """Vector-search the Contoso product catalog and return matching products as JSON."""
    products = product_agent.find_products(context)
    return json.dumps(products)
