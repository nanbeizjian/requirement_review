from fastapi import FastAPI

from requirement_review.api.routes import projects, reviews
from requirement_review.api.runtime import InMemoryApplicationServices
from requirement_review.telemetry import telemetry_middleware


def create_app(services=None) -> FastAPI:
    app = FastAPI(title="Requirement Review API", version="1.0.0")
    app.state.services = services or InMemoryApplicationServices()
    app.middleware("http")(telemetry_middleware)
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    return app


app = create_app()
