"""Multi-agent orchestration for Contoso Creative Writer.

Rewritten on top of the Microsoft Agent Framework (the successor to AutoGen and
Semantic Kernel). The four-agent intent of the original app is preserved:

    researcher -> product marketing -> writer -> editor (with a feedback loop)

The researcher and product agents call function tools (Bing grounding and Azure
AI Search vector retrieval); the writer and editor agents reuse the original
Prompty templates as their prompts so the app's carefully tuned intent is kept.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Literal

import prompty
from prompty.tracer import trace, Tracer, PromptyTracer
from pydantic import BaseModel, Field

from agent_framework_client import build_agent, prompty_instructions
from agents.tools import research_topic, search_products
from agents.writer import writer as writer_utils

# Evaluation deps are optional at runtime (they live in requirements-dev.txt).
try:
    from evaluate.evaluators import evaluate_article_in_background
except Exception:  # noqa: BLE001 - keep the API runnable without the eval stack
    evaluate_article_in_background = None

BASE = Path(__file__).resolve().parent

types = Literal[
    "message", "researcher", "marketing", "designer", "writer", "editor", "error", "partial",
]


class Message(BaseModel):
    type: types
    message: str | dict | None
    data: List | dict = Field(default={})

    def to_json_line(self):
        return self.model_dump_json().replace("\n", "") + "\n"


class Task(BaseModel):
    research: str
    products: str
    assignment: str


DEFAULT_LOG_LEVEL = 25


def log_output(*args):
    logging.log(DEFAULT_LOG_LEVEL, *args)


def start_message(type: types):
    return Message(type="message", message=f"Starting {type} agent task...").to_json_line()


def complete_message(type: types, result):
    return Message(type=type, message=f"Completed {type} task", data=result).to_json_line()


def error_message(error: Exception):
    return Message(type="error", message="An error occurred.", data={"error": str(error)}).to_json_line()


def send_research(research_result):
    return json.dumps(("researcher", research_result))


def send_products(product_result):
    return json.dumps(("products", product_result))


def send_writer(full_result):
    return json.dumps(("writer", full_result))


def building_agents_message():
    return Message(
        type="message", message="Initializing Agent Service, please wait a few seconds..."
    ).to_json_line()


# ---- Agent instructions (intent preserved from the original .prompty files) ----

RESEARCHER_INSTRUCTIONS = (
    prompty_instructions(str(BASE / "agents" / "researcher" / "researcher.prompty"))
    + "\n\nAlways call the `research_topic` tool to gather sources, then return its "
    "JSON verbatim as your final answer."
)

PRODUCT_INSTRUCTIONS = (
    "You are a product marketing assistant for Contoso Outdoors. Given a description "
    "of the products a writer needs, call the `search_products` tool to retrieve "
    "matching catalog items, then return the tool's JSON array verbatim as your final "
    "answer with no extra prose."
)

WRITER_ROLE = "You are an expert copywriter. Follow the detailed brief you are given exactly."
EDITOR_ROLE = "You are a meticulous editor. Respond only with the JSON object requested."


def _extract_json(text: str):
    """Best-effort extraction of a JSON object/array from an agent's text response."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start, end = text.find(open_c), text.rfind(close_c)
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
    return None


def _render_prompty(relative_path: str, inputs: dict) -> str:
    """Render a .prompty template to a single prompt string, preserving the original text."""
    prompt = prompty.load(str(BASE / relative_path))
    messages = prompty.prepare(prompt, inputs)
    parts = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(c) for c in content)
        parts.append(str(content))
    return "\n\n".join(p for p in parts if p)


async def _run_text(agent, prompt: str) -> str:
    result = await agent.run(prompt)
    return getattr(result, "text", str(result))


async def _run_editor(editor, article, feedback):
    prompt = _render_prompty("agents/editor/editor.prompty", {"article": article, "feedback": feedback})
    text = await _run_text(editor, prompt)
    parsed = _extract_json(text)
    if not isinstance(parsed, dict):
        parsed = {"decision": "reject", "editorFeedback": "No Feedback", "researchFeedback": "No Feedback"}
    return parsed


async def _stream_writer(writer, research_context, research, product_context, products, assignment, feedback):
    """Render the writer prompt, stream tokens as partial messages, and return the full text."""
    prompt = _render_prompty(
        "agents/writer/writer.prompty",
        {
            "researchContext": research_context,
            "research": research,
            "productContext": product_context,
            "products": products,
            "assignment": assignment,
            "feedback": feedback,
        },
    )

    async def _gen():
        full = " "
        async for chunk in writer.run(prompt, stream=True):
            text = getattr(chunk, "text", "")
            if text:
                full += text
                yield complete_message("partial", {"text": text})
        yield full

    return _gen()


@trace
async def create(research_context, product_context, assignment_context, evaluate=True):
    feedback = "No Feedback"
    full_text = ""

    yield building_agents_message()

    researcher = build_agent("researcher", RESEARCHER_INSTRUCTIONS, tools=[research_topic])
    marketer = build_agent("product-marketing", PRODUCT_INSTRUCTIONS, tools=[search_products])
    writer = build_agent("writer", WRITER_ROLE)
    editor = build_agent("editor", EDITOR_ROLE)

    # 1. Research
    yield start_message("researcher")
    research_text = await _run_text(researcher, research_context)
    research_result = _extract_json(research_text) or {"web": [], "entities": [], "news": []}
    research_result.setdefault("entities", [])
    research_result.setdefault("news", [])
    yield complete_message("researcher", research_result)

    # 2. Products
    yield start_message("marketing")
    product_text = await _run_text(marketer, product_context)
    product_result = _extract_json(product_text) or []
    yield complete_message("marketing", product_result)

    # 3. Writer (streamed)
    yield start_message("writer")
    yield complete_message("writer", {"start": True})
    async for line in await _stream_writer(
        writer, research_context, research_result, product_context,
        product_result, assignment_context, feedback,
    ):
        if isinstance(line, str) and line.endswith("\n"):
            yield line
        else:
            full_text = line
    processed_writer_result = writer_utils.process(full_text)

    # 4. Editor
    yield start_message("editor")
    editor_response = await _run_editor(
        editor, processed_writer_result["article"], processed_writer_result["feedback"]
    )
    yield complete_message("editor", editor_response)
    yield complete_message("writer", {"complete": True})

    # 5. Feedback loop (behavior preserved from the original orchestrator)
    retry_count = 0
    while str(editor_response.get("decision", "")).lower().startswith("accept"):
        yield Message(type="message", message=f"Sending editor feedback ({retry_count + 1})...").to_json_line()

        research_feedback = editor_response.get("researchFeedback", "No Feedback")
        editor_feedback = editor_response.get("editorFeedback", "No Feedback")

        research_text = await _run_text(researcher, f"{research_context}\n\nFeedback: {research_feedback}")
        research_result = _extract_json(research_text) or research_result
        research_result.setdefault("entities", [])
        research_result.setdefault("news", [])
        yield complete_message("researcher", research_result)

        yield start_message("writer")
        yield complete_message("writer", {"start": True})
        async for line in await _stream_writer(
            writer, research_context, research_result, product_context,
            product_result, assignment_context, editor_feedback,
        ):
            if isinstance(line, str) and line.endswith("\n"):
                yield line
            else:
                full_text = line
        processed_writer_result = writer_utils.process(full_text)

        yield start_message("editor")
        editor_response = await _run_editor(
            editor, processed_writer_result["article"], processed_writer_result["feedback"]
        )

        retry_count += 1
        if retry_count >= 2:
            break

        yield complete_message("editor", editor_response)
        yield complete_message("writer", {"complete": True})

    # Needed by evaluate.evaluate when called externally
    yield send_research(research_result)
    yield send_products(product_result)
    yield send_writer(full_text)

    if evaluate and evaluate_article_in_background is not None:
        print("Evaluating article...")
        evaluate_article_in_background(
            research_context=research_context,
            product_context=product_context,
            assignment_context=assignment_context,
            research=research_result,
            products=product_result,
            article=full_text,
        )


@trace
async def test_create_article(research_context, product_context, assignment_context):
    async for result in create(research_context, product_context, assignment_context, evaluate=False):
        try:
            parsed_result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed_result, dict):
            if parsed_result.get("type") in ("researcher", "marketing", "editor"):
                print(parsed_result["data"])
        if isinstance(parsed_result, list) and parsed_result[0] == "writer":
            print(f"Article: {parsed_result[1]}")


if __name__ == "__main__":
    local_trace = PromptyTracer()
    Tracer.add("PromptyTracer", local_trace.tracer)
    research_context = "Can you find the latest camping trends and what folks are doing in the winter?"
    product_context = "Can you use a selection of tents and sleeping bags as context?"
    assignment_context = (
        "Write a fun and engaging article that includes the research and product information. "
        "The article should be between 800 and 1000 words. "
        "Make sure to cite sources in the article as you mention the research not at the end."
    )
    asyncio.run(
        test_create_article(
            research_context=research_context,
            product_context=product_context,
            assignment_context=assignment_context,
        )
    )
