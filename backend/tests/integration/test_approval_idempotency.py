"""Cover the public-contract idempotency clause on the approval endpoint.

The root `public-contracts` capability requires approval/rejection to be
auditable and idempotent. These tests pin down what "idempotent" means
concretely for `POST /api/v1/reviews/{review_id}/approval`:

- Same `Idempotency-Key` + identical body  -> replay original outcome,
  do not append a second approval entry, do not re-execute the graph.
- Same `Idempotency-Key` + different body -> 409 `idempotency_conflict`
  with the key as correlation identifier.

Both the direct-runtime test (`test_runtime_dedupe`) and the HTTP-layer test
(`test_http_idempotency_conflict`) are expected to fail against the
un-patched implementation in `InMemoryApplicationServices.approve`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from requirement_review.api.app import create_app
from requirement_review.api.runtime import (
    IdempotencyConflictError,
    InMemoryApplicationServices,
)


def _admin_headers() -> dict[str, str]:
    return {"X-User-ID": "admin", "X-Project-ID": "bootstrap", "X-Role": "admin"}


def _reviewer_headers(project_id: str) -> dict[str, str]:
    return {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}


async def _create_review_and_wait(services: InMemoryApplicationServices, project_id: str) -> str:
    body = {
        "project_id": project_id,
        "text": "# Login\n\nThe system shall log in quickly.",
        "data_policy": "local_only",
    }
    result = await services.create_review(body, actor_id="reviewer")
    return result["review_id"]


async def _setup() -> tuple[InMemoryApplicationServices, str]:
    services = InMemoryApplicationServices()
    project = await services.create_project("Idempotency", "local_only", "admin")
    project_id = project["id"]
    review_id = await _create_review_and_wait(services, project_id)
    return services, review_id


# ---------------------------------------------------------------------------
# Direct-runtime test: drives InMemoryApplicationServices.approve directly.
# Verifies the storage layer enforces idempotency before graph resume.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_replays_identical_approval_body() -> None:
    services, review_id = await _setup()
    payload = {"action": "approve", "comment": "looks good"}

    first = await services.approve(
        review_id=review_id,
        project_id=services.reviews[review_id].project_id,
        actor_id="reviewer",
        idempotency_key="idem-1",
        payload=payload,
    )
    record = services.reviews[review_id]
    approvals_after_first = list(record.approvals)

    second = await services.approve(
        review_id=review_id,
        project_id=services.reviews[review_id].project_id,
        actor_id="reviewer",
        idempotency_key="idem-1",
        payload=payload,
    )

    assert first["status"] == "COMPLETED"
    assert second == first
    assert len(record.approvals) == len(approvals_after_first), (
        "identical-body replay must not append a second approval entry"
    )


@pytest.mark.asyncio
async def test_runtime_rejects_different_body_with_same_key() -> None:
    services, review_id = await _setup()
    project_id = services.reviews[review_id].project_id

    await services.approve(
        review_id=review_id,
        project_id=project_id,
        actor_id="reviewer",
        idempotency_key="idem-2",
        payload={"action": "approve", "comment": "looks good"},
    )
    record = services.reviews[review_id]
    approvals_after_first = list(record.approvals)

    with pytest.raises(IdempotencyConflictError):
        await services.approve(
            review_id=review_id,
            project_id=project_id,
            actor_id="reviewer",
            idempotency_key="idem-2",
            payload={"action": "reject", "comment": "changed mind"},
        )

    assert len(record.approvals) == len(approvals_after_first), (
        "conflict must not append a second approval entry"
    )


# ---------------------------------------------------------------------------
# HTTP-layer test: walks the full FastAPI stack and asserts the contract
# response shape (status code, error code, correlation identifier).
# ---------------------------------------------------------------------------


def _seed_review(client: TestClient, project_id: str) -> str:
    created = client.post(
        "/api/v1/reviews",
        headers=_reviewer_headers(project_id),
        json={
            "project_id": project_id,
            "text": "# Login\n\nThe system shall log in quickly.",
            "data_policy": "local_only",
        },
    )
    assert created.status_code == 202
    return created.json()["review_id"]


def _create_project(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/projects",
        headers=_admin_headers(),
        json={"name": "Idempotency", "data_policy": "local_only"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_http_idempotency_conflict_returns_409_with_correlation_id() -> None:
    client = TestClient(create_app(InMemoryApplicationServices()))
    project_id = _create_project(client)
    review_id = _seed_review(client, project_id)
    auth = _reviewer_headers(project_id)

    first = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**auth, "Idempotency-Key": "http-idem-1"},
        json={"action": "approve", "comment": "looks good"},
    )
    assert first.status_code == 202, first.text

    conflict = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**auth, "Idempotency-Key": "http-idem-1"},
        json={"action": "reject", "comment": "changed mind"},
    )
    assert conflict.status_code == 409, conflict.text
    body = conflict.json()
    detail = body["detail"]
    assert detail["code"] == "idempotency_conflict"
    assert detail["correlation_id"] == "http-idem-1"

    # Confirm only the first approval is recorded: the report should contain
    # exactly one approval row, not two.
    report = client.get(f"/api/v1/reviews/{review_id}/report", headers=auth)
    assert report.status_code == 200
    approval_lines = [
        line
        for line in report.text.splitlines()
        if line.startswith("- reviewer:")
    ]
    assert len(approval_lines) == 1, report.text
    assert "looks good" in approval_lines[0]


def test_http_identical_body_replay_does_not_record_second_approval() -> None:
    client = TestClient(create_app(InMemoryApplicationServices()))
    project_id = _create_project(client)
    review_id = _seed_review(client, project_id)
    auth = _reviewer_headers(project_id)

    payload = {"action": "approve", "comment": "looks good"}
    first = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**auth, "Idempotency-Key": "http-idem-replay"},
        json=payload,
    )
    assert first.status_code == 202

    replay = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**auth, "Idempotency-Key": "http-idem-replay"},
        json=payload,
    )
    assert replay.status_code == 202
    assert replay.json() == first.json()

    report = client.get(f"/api/v1/reviews/{review_id}/report", headers=auth)
    approval_lines = [
        line for line in report.text.splitlines() if line.startswith("- reviewer:")
    ]
    assert len(approval_lines) == 1, report.text
