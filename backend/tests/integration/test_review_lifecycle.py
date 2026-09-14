from fastapi.testclient import TestClient

from requirement_review.api.app import create_app
from requirement_review.api.runtime import InMemoryApplicationServices


def test_full_review_lifecycle() -> None:
    client = TestClient(create_app(InMemoryApplicationServices()))
    admin = {"X-User-ID": "admin", "X-Project-ID": "bootstrap", "X-Role": "admin"}
    project = client.post(
        "/api/v1/projects",
        headers=admin,
        json={"name": "Payments", "data_policy": "local_only"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    auth = {"X-User-ID": "reviewer", "X-Project-ID": project_id, "X-Role": "reviewer"}
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/documents",
        headers={**auth, "X-Role": "admin"},
        files={
            "file": (
                "system.md",
                b"# Login\n\nERR_LOGIN_01 means invalid password",
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 202
    created = client.post(
        "/api/v1/reviews",
        headers=auth,
        json={
            "project_id": project_id,
            "text": "# Login\n\nThe system should log in quickly.",
            "data_policy": "local_only",
        },
    )
    assert created.status_code == 202
    review_id = created.json()["review_id"]
    state = client.get(f"/api/v1/reviews/{review_id}", headers=auth)
    assert state.json()["status"] == "WAITING_APPROVAL"
    approved = client.post(
        f"/api/v1/reviews/{review_id}/approval",
        headers={**auth, "Idempotency-Key": "approve-1"},
        json={"action": "approve", "comment": "approved"},
    )
    assert approved.status_code == 202
    assert approved.json()["status"] == "COMPLETED"
    report = client.get(f"/api/v1/reviews/{review_id}/report", headers=auth)
    assert report.status_code == 200
    assert "审批记录" in report.text
