"""Covers the additive extensions in openspec/changes/add-directory-ai-review-workbench/specs/public-contracts/spec.md."""

import pytest
from fastapi.testclient import TestClient

from requirement_review.api.app import create_app
from requirement_review.api.runtime import InMemoryApplicationServices
from requirement_review.domain.models import (
    EvidenceRef,
    ReviewDimension,
    ReviewFinding,
    Severity,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(InMemoryApplicationServices()))


def _bootstrap_project(client: TestClient) -> str:
    r = client.post(
        "/api/v1/projects",
        headers={"X-User-ID": "admin", "X-Project-ID": "bootstrap", "X-Role": "admin"},
        json={"name": "demo", "data_policy": "local_only"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_review(client: TestClient, project_id: str, source_name: str | None = None) -> str:
    body: dict = {"project_id": project_id, "data_policy": "local_only", "text": "# R\n\nSpec text."}
    if source_name is not None:
        body["source_name"] = source_name
    r = client.post(
        "/api/v1/reviews",
        headers={"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"},
        json=body,
    )
    assert r.status_code == 202
    return r.json()["review_id"]


def _seed_findings(services: InMemoryApplicationServices, review_id: str) -> None:
    record = services.reviews[review_id]
    record.findings = [
        ReviewFinding(
            finding_id="f1", requirement_id="req-1", dimension=ReviewDimension.COMPLETENESS,
            severity=Severity.HIGH, issue="x", impact="y", recommendation="z",
            confidence=0.9,
            evidence=[EvidenceRef(source_type="requirement", document_id="d", version=1, locator="L1", quote="q")],
            uses_system_fact=False,
        ),
        ReviewFinding(
            finding_id="f2", requirement_id="req-2", dimension=ReviewDimension.CLARITY,
            severity=Severity.LOW, issue="x2", impact="y2", recommendation="z2",
            confidence=0.5,
            evidence=[EvidenceRef(source_type="requirement", document_id="d", version=1, locator="L2", quote="q2")],
            uses_system_fact=False,
        ),
    ]
    record.findings_locked = True


def test_review_source_metadata_round_trips(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id, source_name="SPEC.md")
    r = client.get(
        f"/api/v1/reviews/{review_id}",
        headers={"X-User-ID": "u", "X-Project-ID": project_id, "X-Role": "viewer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source_name"] == "SPEC.md"
    assert "created_at" in body


def test_list_reviews_scopes_to_project_and_orders_desc(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    a = _create_review(client, project_id, source_name="a.md")
    b = _create_review(client, project_id, source_name="b.md")
    other_project = _bootstrap_project(client)
    _create_review(client, other_project, source_name="other.md")
    r = client.get(
        "/api/v1/reviews",
        headers={"X-User-ID": "u", "X-Project-ID": project_id, "X-Role": "viewer"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert {row["review_id"] for row in rows} == {a, b}
    # Newest first by created_at; tie-breaker is review_id asc.
    for row in rows:
        assert set(row) >= {"review_id", "project_id", "source_name", "status", "finding_count", "pending_decision_count", "created_at"}


def test_cross_project_list_returns_empty(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    _create_review(client, project_id, source_name="in-scope.md")
    r = client.get(
        "/api/v1/reviews",
        headers={"X-User-ID": "u", "X-Project-ID": "other-project", "X-Role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_finding_decision_projection_latest_wins(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    client.post(
        f"/api/v1/reviews/{review_id}/findings/f1/decision",
        headers={**headers, "Idempotency-Key": "k1"},
        json={"action": "accept", "comment": "first"},
    )
    client.post(
        f"/api/v1/reviews/{review_id}/findings/f1/decision",
        headers={**headers, "Idempotency-Key": "k2"},
        json={"action": "reject", "comment": "second"},
    )
    f = client.get(
        f"/api/v1/reviews/{review_id}/findings",
        headers={"X-User-ID": "u", "X-Project-ID": project_id, "X-Role": "viewer"},
    ).json()
    decision = next(x for x in f if x["finding_id"] == "f1")["decision"]
    assert decision is not None
    assert decision["action"] == "reject"
    assert decision["comment"] == "second"
    assert decision["idempotency_key"] == "k2"


def test_decide_idempotency_same_key_same_body_returns_original(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    body = {"action": "accept", "comment": "ok"}
    r1 = client.post(f"/api/v1/reviews/{review_id}/findings/f1/decision", headers={**headers, "Idempotency-Key": "stable"}, json=body)
    r2 = client.post(f"/api/v1/reviews/{review_id}/findings/f1/decision", headers={**headers, "Idempotency-Key": "stable"}, json=body)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json() == r2.json()
    assert sum(1 for (rid, fid, _) in services.decisions if rid == review_id and fid == "f1") == 1


def test_decide_idempotency_same_key_different_body_returns_409(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    client.post(f"/api/v1/reviews/{review_id}/findings/f1/decision", headers={**headers, "Idempotency-Key": "stable"},
                 json={"action": "accept", "comment": "ok"})
    r2 = client.post(f"/api/v1/reviews/{review_id}/findings/f1/decision", headers={**headers, "Idempotency-Key": "stable"},
                     json={"action": "reject", "comment": "changed"})
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "idempotency_conflict"


def test_finalization_gate_rejects_undecided_findings(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    r = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**headers, "Idempotency-Key": "apr-1"},
        json={"action": "approve", "comment": ""},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "approval_blocked_undecided"


def test_finalization_gate_rejects_re_review_decision(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    for fid in ("f1", "f2"):
        action = "accept" if fid == "f1" else "re-review"
        client.post(
            f"/api/v1/reviews/{review_id}/findings/{fid}/decision",
            headers={**headers, "Idempotency-Key": f"k-{fid}"},
            json={"action": action, "comment": ""},
        )
    r = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**headers, "Idempotency-Key": "apr-1"},
        json={"action": "approve", "comment": ""},
    )
    assert r.status_code == 409


def test_finalization_gate_allows_all_resolved_and_zero_findings(client: TestClient) -> None:
    project_id = _bootstrap_project(client)
    review_id = _create_review(client, project_id)
    services: InMemoryApplicationServices = client.app.state.services
    _seed_findings(services, review_id)
    headers = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    for fid in ("f1", "f2"):
        client.post(
            f"/api/v1/reviews/{review_id}/findings/{fid}/decision",
            headers={**headers, "Idempotency-Key": f"k-{fid}"},
            json={"action": "accept", "comment": ""},
        )
    r = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**headers, "Idempotency-Key": "apr-2"},
        json={"action": "approve", "comment": ""},
    )
    assert r.status_code == 202
    assert r.json()["status"] == "COMPLETED"

    # Zero findings: approve immediately, no decisions required
    zero_review_id = _create_review(client, project_id)
    r2 = client.post(
        f"/api/v1/reviews/{zero_review_id}/approval",
        headers={**headers, "Idempotency-Key": "apr-3"},
        json={"action": "approve", "comment": ""},
    )
    assert r2.status_code == 202
