"""Observability wiring: OpenTelemetry traces exported to Application Insights.

Tracing is GA in the Foundry experience. Agent, tool, and model spans emitted by
the Microsoft Agent Framework are exported through OpenTelemetry to the
Application Insights resource attached to the Foundry project, where they show up
in the Agent Monitor / tracing views. Local development can instead emit traces
to the console + Prompty ``.runs`` files.
"""
import contextlib
import json
import os

from fastapi import FastAPI
from azure.core.settings import settings
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace as oteltrace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prompty.tracer import Tracer, PromptyTracer, console_tracer

_tracer = "prompty"


@contextlib.contextmanager
def trace_span(name: str):
    tracer = oteltrace.get_tracer(_tracer)
    with tracer.start_as_current_span(name) as span:
        yield lambda key, value: span.set_attribute(key, json.dumps(value).replace("\n", ""))


def _credential() -> DefaultAzureCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


def _application_insights_connection_string() -> str | None:
    """Prefer an explicit connection string; otherwise read it from the project."""
    conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if conn:
        return conn

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        return None

    try:
        with AIProjectClient(endpoint=endpoint, credential=_credential()) as project:
            return project.telemetry.get_application_insights_connection_string()
    except Exception as exc:  # noqa: BLE001 - telemetry is best-effort
        print(f"Could not read Application Insights connection string from project: {exc}")
        return None


def _enable_agent_framework_observability(connection_string: str | None) -> None:
    """Turn on Agent Framework OpenTelemetry instrumentation (agents, tools, models)."""
    try:
        from agent_framework.observability import setup_observability

        setup_observability(
            applicationinsights_connection_string=connection_string,
            enable_sensitive_data=True,
        )
    except Exception as exc:  # noqa: BLE001 - keep the app running without tracing
        print(f"Agent Framework observability not enabled: {exc}")


def setup_telemetry(app: FastAPI):
    settings.tracing_implementation = "OpenTelemetry"
    local_tracing_enabled = (os.getenv("LOCAL_TRACING_ENABLED") or "").lower() == "true"

    if local_tracing_enabled:
        Tracer.add("console", console_tracer)
        Tracer.add("PromptyTracer", PromptyTracer().tracer)
        _enable_agent_framework_observability(None)
    else:
        connection_string = _application_insights_connection_string()
        if not connection_string:
            print("Application Insights is not configured for this project.")
            print("Set APPLICATIONINSIGHTS_CONNECTION_STRING or enable tracing on the Foundry project.")
        else:
            configure_azure_monitor(connection_string=connection_string)
            Tracer.add("OpenTelemetry", trace_span)
            _enable_agent_framework_observability(connection_string)

    # Instrument FastAPI and exclude the send span to reduce noise
    FastAPIInstrumentor.instrument_app(app, exclude_spans=["send"])
