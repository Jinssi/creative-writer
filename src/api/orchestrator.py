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
from agents.illustrator import generate_hero_image
from agents.image_store import put_image
from agents.writer import writer as writer_utils

# Evaluation deps are optional at runtime (they live in requirements-dev.txt).
try:
    from evaluate.evaluators import evaluate_article_in_background
except Exception:  # noqa: BLE001 - keep the API runnable without the eval stack
    evaluate_article_in_background = None

BASE = Path(__file__).resolve().parent

types = Literal[
    "message", "researcher", "marketing", "designer", "writer", "editor",
    "factchecker", "repurposer", "error", "partial",
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
    "You are a research assistant that finds reference material for a writer. Given a "
    "description of the references or examples the writer needs, call the `search_products` "
    "tool to retrieve matching items, then return the tool's JSON array verbatim as your "
    "final answer with no extra prose. If the tool returns an empty array, return []."
)

WRITER_ROLE = "You are an expert copywriter. Follow the detailed brief you are given exactly."
EDITOR_ROLE = "You are a meticulous editor. Respond only with the JSON object requested."

FACT_CHECKER_INSTRUCTIONS = (
    "You are a fact-checker. You are given an article and the list of web sources that were "
    "gathered for it. Verify the article's key factual claims strictly against those sources. "
    "Return ONLY a JSON object shaped as "
    '{"status": "supported|mixed|unsupported", "summary": "one sentence", '
    '"claims": [{"claim": "", "status": "supported|unsupported|uncertain", "source": "url or empty"}]}. '
    "Judge up to 6 of the most important claims. A claim is 'supported' only if a provided source "
    "backs it; 'uncertain' if no source addresses it; 'unsupported' if a source contradicts it. "
    "No prose outside the JSON, no code fences."
)

ILLUSTRATOR_INSTRUCTIONS = (
    "You are an art director. Given an article and its creative theme, write ONE concise, vivid "
    "image-generation prompt (max 60 words) for a tasteful editorial hero image that fits the "
    "article. Describe subject, setting, mood, style and color palette. Do not include any text, "
    "words, logos or watermarks in the image. Return ONLY the prompt text, nothing else."
)

REPURPOSER_INSTRUCTIONS = (
    "You are a social media manager. Given a finished article, repurpose it for distribution. "
    "Return ONLY a JSON object shaped as "
    '{"linkedin": "", "x_thread": ["", ""], "newsletter": ""}. '
    "'linkedin' is a professional post (<= 120 words) with 2-3 relevant hashtags. 'x_thread' is "
    "2-4 short posts (<= 280 chars each) that summarize the article as a thread. 'newsletter' is a "
    "2-3 sentence teaser blurb. No prose outside the JSON, no code fences."
)


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


async def _run_factcheck(fact_checker, article, research_result):
    sources = (research_result or {}).get("web", []) if isinstance(research_result, dict) else []
    sources_text = "\n".join(
        f"- {s.get('name', '')}: {s.get('url', '')} — {s.get('description', '')}"
        for s in sources if isinstance(s, dict)
    ) or "(no sources were gathered)"
    text = await _run_text(fact_checker, f"SOURCES:\n{sources_text}\n\nARTICLE:\n{article}")
    parsed = _extract_json(text)
    if not isinstance(parsed, dict):
        parsed = {"status": "uncertain", "summary": "Fact-check unavailable.", "claims": []}
    parsed.setdefault("claims", [])
    return parsed


async def _run_illustrate(illustrator, article, assignment_context):
    prompt_text = (
        await _run_text(illustrator, f"THEME/BRIEF:\n{assignment_context}\n\nARTICLE:\n{article[:4000]}")
    ).strip().strip('"')
    # Image generation is blocking network I/O — run it off the event loop.
    image = await asyncio.to_thread(generate_hero_image, prompt_text) if prompt_text else None
    # Keep the (large) base64 out of the stream: store it and stream only an id.
    image_id = put_image(image) if image else None
    return {"prompt": prompt_text, "image_id": image_id}


async def _run_repurpose(repurposer, article):
    text = await _run_text(repurposer, article)
    parsed = _extract_json(text)
    if not isinstance(parsed, dict):
        parsed = {"linkedin": "", "x_thread": [], "newsletter": ""}
    parsed.setdefault("x_thread", [])
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

    marketer = build_agent("product-marketing", PRODUCT_INSTRUCTIONS, tools=[search_products])
    writer = build_agent("writer", WRITER_ROLE)
    editor = build_agent("editor", EDITOR_ROLE)
    fact_checker = build_agent("fact-checker", FACT_CHECKER_INSTRUCTIONS)
    illustrator = build_agent("illustrator", ILLUSTRATOR_INSTRUCTIONS)
    repurposer = build_agent("repurposer", REPURPOSER_INSTRUCTIONS)

    # 1. Research — call the grounding tool directly so sources are deterministic
    #    (relying on an LLM to "decide" to call the tool was dropping all sources).
    yield start_message("researcher")
    research_raw = await asyncio.to_thread(research_topic, research_context)
    research_result = _extract_json(research_raw) or {"web": [], "entities": [], "news": []}
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

        research_raw = await asyncio.to_thread(
            research_topic, f"{research_context}\n\nFeedback: {research_feedback}"
        )
        research_result = _extract_json(research_raw) or research_result
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

    final_article = processed_writer_result["article"]

    # 6. Fact-checker (fact-checker-CW): verify claims against the gathered sources
    yield start_message("factchecker")
    try:
        factcheck = await _run_factcheck(fact_checker, final_article, research_result)
    except Exception as exc:  # noqa: BLE001 - post-processing is best-effort
        factcheck = {"status": "uncertain", "summary": f"Fact-check skipped: {exc}", "claims": []}
    yield complete_message("factchecker", factcheck)

    # 7. Illustrator (illustrator-CW): craft a prompt and render a hero image
    yield start_message("designer")
    try:
        design = await _run_illustrate(illustrator, final_article, assignment_context)
    except Exception as exc:  # noqa: BLE001 - illustration is best-effort
        print(f"illustration skipped: {exc}")
        design = {"prompt": "", "image_id": None}
    yield complete_message("designer", design)

    # 8. Repurposer (repurposer-CW): social + newsletter variants
    yield start_message("repurposer")
    try:
        repurposed = await _run_repurpose(repurposer, final_article)
    except Exception as exc:  # noqa: BLE001 - repurposing is best-effort
        repurposed = {"linkedin": "", "x_thread": [], "newsletter": ""}
    yield complete_message("repurposer", repurposed)

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
