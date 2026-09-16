import os
import time
import warnings
from typing import Literal
from uuid import uuid4

import structlog
from fastapi import Request
from opentelemetry import trace

tracer = trace.get_tracer("requirement-review")


def bind_review_context(
    request_id: str, review_id: str | None = None, thread_id: str | None = None
):
    return structlog.get_logger().bind(
        request_id=request_id, review_id=review_id, thread_id=thread_id
    )


# ---------------------------------------------------------------------------
# LangSmith trace export
#
# langchain-core auto-detects these env vars at import time and starts
# uploading spans to LangSmith. We mirror that here so:
#   1. Mismatched config (TRACING_V2=true without API_KEY) warns early
#      instead of failing silently inside a LangChain call.
#   2. We can prove the configuration was read in a unit test.
# ---------------------------------------------------------------------------

LangSmithStatus = Literal["enabled", "disabled", "misconfigured"]


def configure_langsmith() -> LangSmithStatus:
    """Validate LangSmith env vars and warn on misconfiguration.

    Reads:
      LANGCHAIN_TRACING_V2  (truthy values: "true"/"1"/"yes")
      LANGCHAIN_API_KEY     (must be a non-empty string starting with `lsv2_`)
      LANGCHAIN_PROJECT     (defaults to "requirement-review")

    Returns one of:
      "enabled"      — TRACING_V2=true AND API_KEY is set
      "disabled"     — TRACING_V2 not true (trace stays local)
      "misconfigured"— TRACING_V2=true but API_KEY missing/invalid

    langchain-core picks up these env vars on first call; this helper only
    surfaces their state so it can be tested and so the operator gets
    immediate feedback if config is wrong.
    """
    tracing = os.environ.get("LANGCHAIN_TRACING_V2", "").lower()
    enabled = tracing in {"true", "1", "yes"}
    api_key = os.environ.get("LANGCHAIN_API_KEY", "").strip()
    project = os.environ.get("LANGCHAIN_PROJECT", "requirement-review").strip() or "requirement-review"
    endpoint = os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    if not enabled:
        bind_review_context("").info(
            "langsmith_tracing_disabled",
            reason="LANGCHAIN_TRACING_V2 not set to true",
            project=project,
            endpoint=endpoint,
        )
        return "disabled"

    if not api_key or not api_key.startswith("lsv2_"):
        warnings.warn(
            "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY is missing or malformed. "
            "LangSmith trace export is disabled until you set LANGCHAIN_API_KEY=lsv2_... .",
            stacklevel=2,
        )
        return "misconfigured"

    bind_review_context("").info(
        "langsmith_tracing_enabled",
        project=project,
        endpoint=endpoint,
        key_prefix=api_key[:9] + "...",
    )
    return "enabled"


async def telemetry_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.monotonic()
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("request.id", request_id)
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    duration_ms = (time.monotonic() - started) * 1000.0
    bind_review_context(request_id).info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        review_id=request.headers.get("X-Review-ID"),
        thread_id=request.headers.get("X-Thread-ID"),
    )
    return response
