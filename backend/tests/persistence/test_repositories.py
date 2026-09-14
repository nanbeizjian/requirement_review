import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from requirement_review.persistence.repositories import ReviewRepository
from requirement_review.persistence.tables import (
    Base,
    ProjectTable,
    ReviewFindingTable,
    ReviewRunTable,
)


@pytest.fixture
def review_repository() -> ReviewRepository:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(ProjectTable(id="p1", name="Payments", data_policy="local_only"))
    session.add(
        ReviewRunTable(id="r1", project_id="p1", thread_id="t1", status="PENDING")
    )
    session.add(
        ReviewFindingTable(
            id="f1",
            project_id="p1",
            review_id="r1",
            requirement_id="REQ-001",
            dimension="clarity",
            severity="high",
            payload={},
        )
    )
    session.commit()
    return ReviewRepository(session)


@pytest.mark.asyncio
async def test_review_cannot_be_loaded_through_another_project(
    review_repository,
) -> None:
    assert await review_repository.get_for_project("r1", "other-project") is None
    assert (await review_repository.get_for_project("r1", "p1")).id == "r1"


@pytest.mark.asyncio
async def test_same_idempotency_key_does_not_duplicate_decision(
    review_repository,
) -> None:
    first = await review_repository.record_finding_decision(
        "f1", "accept", "u1", "key-1"
    )
    second = await review_repository.record_finding_decision(
        "f1", "accept", "u1", "key-1"
    )
    assert first.id == second.id


@pytest.mark.asyncio
async def test_published_report_versions_are_unique(review_repository) -> None:
    first = await review_repository.publish_report("r1", "p1", "# report")
    second = await review_repository.publish_report("r1", "p1", "# next")
    assert (first.version, second.version) == (1, 2)


@pytest.mark.asyncio
async def test_published_report_cannot_be_updated(review_repository) -> None:
    report = await review_repository.publish_report("r1", "p1", "# report")
    with pytest.raises(ValueError, match="immutable"):
        await review_repository.replace_report(report.id, "changed")


@pytest.mark.asyncio
async def test_decision_rejects_cross_project_finding(review_repository) -> None:
    with pytest.raises(PermissionError):
        await review_repository.record_finding_decision(
            "f1", "accept", "u1", "key-2", project_id="other-project"
        )


def test_all_child_tables_are_project_scoped() -> None:
    exempt = {"projects"}
    for table in Base.metadata.sorted_tables:
        if table.name not in exempt:
            assert "project_id" in table.c, table.name


def test_required_schema_tables_exist() -> None:
    expected = {
        "projects",
        "project_members",
        "source_documents",
        "document_chunks",
        "review_runs",
        "requirement_items",
        "review_findings",
        "finding_decisions",
        "report_approvals",
        "review_reports",
        "audit_events",
    }
    assert expected == set(Base.metadata.tables)
