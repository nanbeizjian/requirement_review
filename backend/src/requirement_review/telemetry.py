import time
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


async def telemetry_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.monotonic()
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("request.id", request_id)
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    bind_review_context(request_id).info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )
    return response
