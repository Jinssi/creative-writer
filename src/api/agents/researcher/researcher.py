"""Backward-compatible researcher shim.

The research capability now lives in ``agents.tools.research_topic`` and is driven
by the Microsoft Agent Framework researcher agent in ``orchestrator.py``. This
module keeps the original ``research(instructions, feedback)`` interface so any
external callers (notebooks, tests) keep working, delegating to the modern tool.
"""
import json
import sys

from prompty.tracer import trace

from agents.tools import research_topic


@trace
def research(instructions: str, feedback: str = "No feedback"):
    result = json.loads(research_topic(instructions))
    return {
        "web": result.get("web", []),
        "entities": result.get("entities", []),
        "news": result.get("news", []),
    }


if __name__ == "__main__":
    instructions = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Can you find the latest camping trends and what folks are doing in the winter?"
    )
    print(json.dumps(research(instructions), indent=2))
