from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from requirement_review.api.app import create_app


@dataclass
class FakeServices:
    approvals: list[dict] = field(default_factory=list)

    async def create_project(self, name: str, data_policy: str, actor_id: str) -> dict:
        return {"id": "p1", "name": name, "data_policy": data_policy}

    async def add_knowledge(
        self, project_id: str, filename: str, content: bytes
    ) -> dict:
        return {"document_id": "k1", "status": "INDEXED"}

    async def reindex(self, project_id: str) -> dict:
        return {"project_id": project_id, "status": "INDEXED"}

    async def create_review(self, payload: dict, actor_id: str) -> dict:
        return {"review_id": "r1", "status": "PENDING"}

    async def get_review(self, review_id: str, project_id: str) -> dict | None:
        return {
            "review_id": review_id,
            "project_id": project_id,
            "source_name": None,
            "status": "WAITING_APPROVAL",
            "finding_count": 0,
            "pending_decision_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "failed_dimensions": [],
        }

    async def list_reviews(self, project_id: str) -> list[dict]:
        return []

    async def get_findings(self, review_id: str, project_id: str) -> list[dict]:
        return []

    async def decide_finding(
        self,
        review_id: str,
        finding_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        return {"finding_id": finding_id, "action": payload["action"]}

    async def approve(
        self,
        review_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        self.approvals.append(payload)
        return {"review_id": review_id, "status": "RESUMING"}

    async def get_report(self, review_id: str, project_id: str) -> str | None:
        return "# report"


def headers(role: str = "reviewer") -> dict[str, str]:
    return {"X-User-ID": "u1", "X-Project-ID": "p1", "X-Role": role}


def test_create_review_returns_202_and_location() -> None:
    client = TestClient(create_app(FakeServices()))
    response = client.post(
        "/api/v1/reviews",
        headers=headers(),
        json={"project_id": "p1", "document_id": "d1", "data_policy": "local_only"},
    )
    assert response.status_code == 202
    assert response.json() == {"review_id": "r1", "status": "PENDING"}
    assert response.headers["Location"] == "/api/v1/reviews/r1"


def test_viewer_cannot_approve() -> None:
    client = TestClient(create_app(FakeServices()))
    response = client.post(
        "/api/v1/reviews/r1/approval",
        headers={**headers("viewer"), "Idempotency-Key": "approve-1"},
        json={"action": "approve", "comment": "同意"},
    )
    assert response.status_code == 403


def test_reviewer_can_resume_waiting_review() -> None:
    services = FakeServices()
    client = TestClient(create_app(services))
    response = client.post(
        "/api/v1/reviews/r1/approval",
        headers={**headers(), "Idempotency-Key": "approve-2"},
        json={"action": "approve", "comment": "同意"},
    )
    assert response.status_code == 202
    assert services.approvals == [
        {"action": "approve", "comment": "同意", "dimensions": None, "findings": None}
    ]


def test_cross_project_request_is_rejected() -> None:
    client = TestClient(create_app(FakeServices()))
    response = client.post(
        "/api/v1/reviews",
        headers={"X-User-ID": "u1", "X-Project-ID": "p2", "X-Role": "reviewer"},
        json={"project_id": "p1", "document_id": "d1", "data_policy": "local_only"},
    )
    assert response.status_code == 404
