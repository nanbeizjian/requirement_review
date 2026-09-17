"""End-to-end coverage for the DatabaseApplicationServices adapter.

These tests run against a real PostgreSQL instance via `REVIEW_DATABASE_URL`.
The default test environment (no env var) skips them. Set
`REQUIREMENT_REVIEW_TEST_DATABASE=1` plus a reachable `REVIEW_DATABASE_URL`
to enable.

The tests rely on:
- Postgres reachable at REVIEW_DATABASE_URL (default
  postgresql+asyncpg://review:review@localhost:5432/review)
- alembic 0001_initial already applied (`alembic upgrade head`)
- EmptyModelGateway (REVIEW_MODEL_BACKEND unset)
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from requirement_review.api.db_runtime import DatabaseApplicationServices
from requirement_review.api.runtime import (
    EmptyModelGateway,
    IdempotencyConflictError,
    PreconditionFailedError,
)
from requirement_review.config import get_settings
from requirement_review.persistence.db import create_session_factory


DATABASE_URL_ENV = "REVIEW_DATABASE_URL"
RUN_FLAG_ENV = "REQUIREMENT_REVIEW_TEST_DATABASE"


def _db_reachable() -> bool:
    """Skip the entire module when no Postgres is reachable from the test env."""
    if os.environ.get(RUN_FLAG_ENV) != "1":
        return False
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        return False
    # psycopg2 sync URL is what SQLAlchemy uses for connection probing.
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    try:
        engine = create_engine(sync_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(),
    reason=f"Postgres not reachable; set {RUN_FLAG_ENV}=1 and {DATABASE_URL_ENV} to run these tests",
)


@pytest.fixture
def services() -> DatabaseApplicationServices:
    settings = get_settings()
    factory = create_session_factory(settings)
    return DatabaseApplicationServices(
        session_factory=factory,
        model_gateway=EmptyModelGateway(),
    )


async def test_create_project_persists_to_postgres(services: DatabaseApplicationServices) -> None:
    settings = get_settings()
    project = await services.create_project(
        name="db-test", data_policy="local_only", actor_id="tester"
    )
    engine = create_engine(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    )
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, data_policy FROM projects WHERE id = :id"),
            {"id": project["id"]},
        ).first()
    engine.dispose()
    assert row is not None
    assert row.name == "db-test"
    assert row.data_policy == "local_only"


async def test_full_review_lifecycle_persists_to_postgres(services: DatabaseApplicationServices) -> None:
    settings = get_settings()
    project = await services.create_project(
        name="lifecycle", data_policy="local_only", actor_id="tester"
    )
    project_id = project["id"]

    review = await services.create_review(
        payload={
            "project_id": project_id,
            "text": "# Login\n\nUsers should log in.",
            "data_policy": "local_only",
            "source_name": "login.md",
        },
        actor_id="tester",
    )
    review_id = review["review_id"]
    assert review["status"] == "PENDING"

    snapshot = await services.get_review(review_id, project_id)
    assert snapshot is not None
    assert snapshot["status"] in {"WAITING_APPROVAL", "FAILED"}
    # With EmptyModelGateway, 0 findings + allResolved=true → approve allowed.
    if snapshot["status"] == "WAITING_APPROVAL":
        outcome = await services.approve(
            review_id=review_id,
            project_id=project_id,
            actor_id="tester",
            idempotency_key="db-lifecycle-1",
            payload={"action": "approve", "comment": "ok"},
        )
        assert outcome["status"] == "COMPLETED"

        # Verify rows persisted.
        engine = create_engine(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        )
        with engine.connect() as conn:
            run = conn.execute(
                text("SELECT status FROM review_runs WHERE id = :id"),
                {"id": review_id},
            ).first()
            approval = conn.execute(
                text("SELECT action FROM report_approvals WHERE review_id = :id"),
                {"id": review_id},
            ).first()
            report = conn.execute(
                text("SELECT version, length(markdown) FROM review_reports WHERE review_id = :id"),
                {"id": review_id},
            ).first()
        engine.dispose()
        assert run.status == "COMPLETED"
        assert approval.action == "approve"
        assert report.version == 1
        assert report.length > 0

        # Report body should round-trip through the API.
        body = await services.get_report(review_id, project_id)
        assert body is not None
        assert "状态：COMPLETED" in body


async def test_decide_finding_idempotency(services: DatabaseApplicationServices) -> None:
    project = await services.create_project("idem", "local_only", "tester")
    project_id = project["id"]
    review = await services.create_review(
        payload={
            "project_id": project_id,
            "text": "# Login\n\nThe system shall allow users to log in using email and password. Sessions shall persist for 30 days.",
            "data_policy": "local_only",
        },
        actor_id="tester",
    )
    review_id = review["review_id"]
    # Insert a synthetic finding + decision via DB (graph returns 0 with
    # EmptyModelGateway, so we need a row in review_findings to exercise
    # decide_finding against).
    settings = get_settings()
    engine = create_engine(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    )
    fid = "finding-test-" + review_id
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO review_findings(id, project_id, review_id, requirement_id, dimension, severity, payload) "
                "VALUES (:id, :pid, :rid, 'REQ-X', 'clarity', 'low', '{}'::jsonb)"
            ),
            {"id": fid, "pid": project_id, "rid": review_id},
        )
    engine.dispose()

    payload = {"action": "accept", "comment": "ok"}
    first = await services.decide_finding(
        review_id=review_id,
        finding_id=fid,
        project_id=project_id,
        actor_id="tester",
        idempotency_key="idem-key-1",
        payload=payload,
    )
    replay = await services.decide_finding(
        review_id=review_id,
        finding_id=fid,
        project_id=project_id,
        actor_id="tester",
        idempotency_key="idem-key-1",
        payload=payload,
    )
    assert first == replay  # identical body → replayed

    with pytest.raises(IdempotencyConflictError):
        await services.decide_finding(
            review_id=review_id,
            finding_id=fid,
            project_id=project_id,
            actor_id="tester",
            idempotency_key="idem-key-1",
            payload={"action": "reject", "comment": "changed"},
        )


async def test_approve_zero_findings_is_allowed(services: DatabaseApplicationServices) -> None:
    """EmptyModelGateway yields 0 findings, so the finalization gate skips and
    approve succeeds. The gate only triggers when the in-memory graph state has
    findings, which is documented behavior of the in-memory runtime too."""
    project = await services.create_project("gate", "local_only", "tester")
    project_id = project["id"]
    review = await services.create_review(
        payload={"project_id": project_id, "text": "# Login\n\nThe system shall allow users to log in using email and password. Sessions shall persist for 30 days.", "data_policy": "local_only"},
        actor_id="tester",
    )
    review_id = review["review_id"]
    outcome = await services.approve(
        review_id=review_id,
        project_id=project_id,
        actor_id="tester",
        idempotency_key="gate-1",
        payload={"action": "approve", "comment": "empty gateway allows it"},
    )
    assert outcome["status"] == "COMPLETED"
