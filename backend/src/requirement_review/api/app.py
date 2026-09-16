import os

from fastapi import FastAPI

from requirement_review.api.routes import projects, reviews
from requirement_review.api.runtime import InMemoryApplicationServices
from requirement_review.telemetry import configure_langsmith, telemetry_middleware

# Configure LangSmith tracing from env vars at process start. langchain-core
# reads the same env vars on its own, but we surface their state here so the
# operator gets immediate feedback (a warning instead of a silent no-op).
_LANGSMITH_STATUS = configure_langsmith() if os.environ.get("REQUIREMENT_REVIEW_SKIP_LANGSMITH_BOOT") != "1" else "disabled"


def create_app(services=None) -> FastAPI:
    app = FastAPI(title="Requirement Review API", version="1.0.0")
    app.state.services = services or InMemoryApplicationServices()
    app.middleware("http")(telemetry_middleware)
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    return app


app = create_app()
