import logging
import os

from fastapi import FastAPI

from requirement_review.api.routes import projects, reviews
from requirement_review.api.runtime import InMemoryApplicationServices
from requirement_review.config import get_settings
from requirement_review.persistence.db import create_session_factory
from requirement_review.model_gateway import (
    ModelProviderConfig,
    ModelGatewayConfigError,
    PolicyModelGateway,
)
from requirement_review.model_gateway.factory import build_resilient_cloud_gateway
from requirement_review.telemetry import configure_langsmith, telemetry_middleware

logger = logging.getLogger("requirement_review.bootstrap")

# Configure LangSmith tracing from env vars at process start. langchain-core
# reads the same env vars on its own, but we surface their state here so the
# operator gets immediate feedback (a warning instead of a silent no-op).
_LANGSMITH_STATUS = configure_langsmith() if os.environ.get("REQUIREMENT_REVIEW_SKIP_LANGSMITH_BOOT") != "1" else "disabled"


def _resolve_model_backend() -> str:
    return os.environ.get("REVIEW_MODEL_BACKEND", "").strip().lower()


def _build_real_model_services() -> InMemoryApplicationServices:
    """Build an InMemoryApplicationServices instance backed by a real model gateway.

    Raises `ModelGatewayConfigError` if the configured backend is missing or
    required environment variables (e.g. `MINIMAX_API_KEY`) are not set.
    """
    backend = _resolve_model_backend()
    if backend not in {"real", "minimax", "cloud"}:
        # Treat any non-empty value as opt-in to fail-fast.
        raise ModelGatewayConfigError(
            f"unsupported REVIEW_MODEL_BACKEND={backend!r}; use 'real' or leave unset"
        )

    config = ModelProviderConfig.from_env()
    cloud = build_resilient_cloud_gateway(config)
    # The cloud client itself decides when to redact (driven by `data_policy`
    # passed at call time). Provide a dedicated client for the redacted path
    # so the same transport config is reused.
    redacted = build_resilient_cloud_gateway(config)
    redacted.inner.redact_for_cloud = True

    class _RoutingCloud:
        async def review(self, **kwargs):
            client = redacted if kwargs.get("data_policy") and str(kwargs["data_policy"]).endswith("REDACTED") else cloud
            return await client.review(**kwargs)

    class _LocalStub:
        async def review(self, **kwargs):
            raise ModelGatewayConfigError(
                "no local gateway configured; data_policy=local_only is unavailable"
            )

    gateway = PolicyModelGateway(local=_LocalStub(), cloud=_RoutingCloud())
    services = InMemoryApplicationServices(model_gateway=gateway)
    services.cloud_client = cloud  # type: ignore[attr-defined]
    services.redacted_client = redacted  # type: ignore[attr-defined]
    services.model_provider_config = config  # type: ignore[attr-defined]
    return services


def create_app(services=None) -> FastAPI:
    app = FastAPI(title="Requirement Review API", version="1.0.0")
    if services is None:
        backend = _resolve_model_backend()
        if backend in {"real", "minimax", "cloud"}:
            try:
                services = _build_real_model_services()
            except ModelGatewayConfigError as exc:
                # Fail fast: a misconfigured production deployment must not
                # silently fall back to EmptyModelGateway. Surface the error
                # and stop the process.
                logger.error("model gateway config error: %s", exc)
                raise
        else:
            if backend:
                logger.warning(
                    "unknown REVIEW_MODEL_BACKEND=%r; falling back to EmptyModelGateway",
                    backend,
                )
            services = InMemoryApplicationServices()

    # Persistence adapter: opt-in via REQUIREMENT_REVIEW_USE_DATABASE=1.
    # When set and REVIEW_DATABASE_URL is configured, promote the in-memory
    # services to a DB-backed implementation that satisfies the same Protocol.
    # Tests that pass InMemoryApplicationServices explicitly get to keep it
    # (no auto-promotion) unless they set this flag.
    use_db = os.environ.get("REQUIREMENT_REVIEW_USE_DATABASE", "").strip() in {"1", "true", "yes"}
    if use_db and services is not None and isinstance(services, InMemoryApplicationServices):
        settings = get_settings()
        if settings.database_url:
            from requirement_review.api.db_runtime import DatabaseApplicationServices
            session_factory = create_session_factory(settings)
            services = DatabaseApplicationServices(
                session_factory=session_factory,
                model_gateway=services.model_gateway,
            )
            logger.info(
                "using DatabaseApplicationServices db=%s", settings.database_url.split("@")[-1]
            )
        else:
            logger.warning(
                "REQUIREMENT_REVIEW_USE_DATABASE=1 but REVIEW_DATABASE_URL is empty; staying in-memory"
            )
    app.state.services = services
    app.state.model_backend = _resolve_model_backend() or "empty"
    app.middleware("http")(telemetry_middleware)
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    return app


app = create_app()
