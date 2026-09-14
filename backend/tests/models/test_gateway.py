from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from requirement_review.domain.models import (
    DataPolicy,
    EvidenceRef,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
)
from requirement_review.models.gateway import PolicyModelGateway


class KnowledgeChunkWithEvidence(KnowledgeChunk):
    """Represents a future knowledge schema that includes quoted evidence."""

    evidence: list[EvidenceRef]


class KnowledgeChunkWithNestedBodies(KnowledgeChunk):
    """Represents a future knowledge schema with structured body content."""

    body: list[object]
    metadata: dict[str, object]


class NestedBodyPart(BaseModel):
    value: str
    identifier: str


@pytest.fixture
def requirement_item() -> RequirementItem:
    return RequirementItem(
        requirement_id="REQ-001",
        text="Customer account number must remain private.",
        evidence=EvidenceRef(
            source_type="requirement",
            document_id="requirements.md",
            version=1,
            locator="Security#1",
            quote="Customer account number must remain private.",
        ),
    )


@pytest.mark.asyncio
async def test_local_only_never_calls_cloud(requirement_item: RequirementItem) -> None:
    """Fails if the local-only route is changed to send any request to cloud."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    gateway = PolicyModelGateway(
        local_model=local, cloud_model=cloud, redactor=lambda value: value
    )

    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.LOCAL_ONLY,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=[],
    )

    local.assert_awaited_once_with(
        project_id="p1",
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=[],
    )
    cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_allowed_sends_original_content_only_to_cloud(
    requirement_item: RequirementItem,
) -> None:
    """Fails if cloud-allowed requests are sent locally or altered before cloud delivery."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    knowledge = [
        KnowledgeChunk(
            chunk_id="chunk-1",
            project_id="p1",
            document_id="architecture.md",
            version=1,
            locator="Database#2",
            text="The account number is encrypted at rest.",
        )
    ]
    gateway = PolicyModelGateway(
        local_model=local,
        cloud_model=cloud,
        redactor=lambda value: f"redacted:{value}",
    )

    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_ALLOWED,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=knowledge,
    )

    local.assert_not_awaited()
    cloud.assert_awaited_once_with(
        project_id="p1",
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=knowledge,
    )


@pytest.mark.asyncio
async def test_cloud_redacted_sends_redacted_requirement_and_all_knowledge_to_cloud(
    requirement_item: RequirementItem,
) -> None:
    """Fails if a cloud-redacted body reaches cloud without redaction."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    knowledge = [
        KnowledgeChunk(
            chunk_id="chunk-1",
            project_id="p1",
            document_id="architecture.md",
            version=1,
            locator="Database#2",
            text="The account number is encrypted at rest.",
        ),
        KnowledgeChunkWithEvidence(
            chunk_id="chunk-2",
            project_id="p1",
            document_id="runbook.md",
            version=3,
            locator="Access#4",
            text="Administrators can view customer account numbers.",
            score=0.75,
            evidence=[
                EvidenceRef(
                    source_type="knowledge",
                    document_id="runbook.md",
                    version=3,
                    locator="Access#4",
                    quote="Administrators can view customer account numbers.",
                )
            ],
        ),
    ]
    gateway = PolicyModelGateway(
        local_model=local,
        cloud_model=cloud,
        redactor=lambda value: "[REDACTED]",
    )

    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_REDACTED,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=knowledge,
    )

    local.assert_not_awaited()
    cloud.assert_awaited_once_with(
        project_id="p1",
        dimension=ReviewDimension.SECURITY,
        requirement=RequirementItem(
            requirement_id="REQ-001",
            text="[REDACTED]",
            evidence=EvidenceRef(
                source_type="requirement",
                document_id="requirements.md",
                version=1,
                locator="Security#1",
                quote="[REDACTED]",
            ),
        ),
        knowledge=[
            KnowledgeChunk(
                chunk_id="chunk-1",
                project_id="p1",
                document_id="architecture.md",
                version=1,
                locator="Database#2",
                text="[REDACTED]",
            ),
            KnowledgeChunkWithEvidence(
                chunk_id="chunk-2",
                project_id="p1",
                document_id="runbook.md",
                version=3,
                locator="Access#4",
                text="[REDACTED]",
                score=0.75,
                evidence=[
                    EvidenceRef(
                        source_type="knowledge",
                        document_id="runbook.md",
                        version=3,
                        locator="Access#4",
                        quote="[REDACTED]",
                    )
                ],
            ),
        ],
    )
    assert requirement_item.text == "Customer account number must remain private."
    assert [chunk.text for chunk in knowledge] == [
        "The account number is encrypted at rest.",
        "Administrators can view customer account numbers.",
    ]
    cloud_payload = repr(cloud.await_args.kwargs)
    assert "Customer account number must remain private." not in cloud_payload
    assert "The account number is encrypted at rest." not in cloud_payload
    assert "Administrators can view customer account numbers." not in cloud_payload


@pytest.mark.asyncio
async def test_unknown_policy_fails_closed_without_calling_any_provider(
    requirement_item: RequirementItem,
) -> None:
    """Fails if a newly introduced policy silently sends data to either provider."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    gateway = PolicyModelGateway(
        local_model=local, cloud_model=cloud, redactor=lambda value: value
    )

    with pytest.raises(ValueError, match="unsupported data policy"):
        await gateway.review(
            project_id="p1",
            data_policy="unknown",  # type: ignore[arg-type]
            dimension=ReviewDimension.SECURITY,
            requirement=requirement_item,
            knowledge=[],
        )

    local.assert_not_awaited()
    cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_redacted_redacts_all_strings_nested_in_a_body_container(
    requirement_item: RequirementItem,
) -> None:
    """Fails if a body container drops the redaction context for a nested string."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    knowledge = [
        KnowledgeChunkWithNestedBodies(
            chunk_id="chunk-3",
            project_id="p1",
            document_id="schema.md",
            version=2,
            locator="Profiles#7",
            text="A separate secret body.",
            body=[
                "SECRET-IN-LIST",
                {"nested": "SECRET-IN-DICT", "items": ["SECRET-IN-NESTED-LIST"]},
            ],
            metadata={"source": "internal", "labels": ["security"]},
        )
    ]
    gateway = PolicyModelGateway(
        local_model=local,
        cloud_model=cloud,
        redactor=lambda value: "[REDACTED]",
    )

    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_REDACTED,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=knowledge,
    )

    local.assert_not_awaited()
    sent_knowledge = cloud.await_args.kwargs["knowledge"]
    assert sent_knowledge == [
        KnowledgeChunkWithNestedBodies(
            chunk_id="chunk-3",
            project_id="p1",
            document_id="schema.md",
            version=2,
            locator="Profiles#7",
            text="[REDACTED]",
            body=[
                "[REDACTED]",
                {"nested": "[REDACTED]", "items": ["[REDACTED]"]},
            ],
            metadata={"source": "internal", "labels": ["security"]},
        )
    ]
    cloud_payload = repr(cloud.await_args.kwargs)
    assert "SECRET-IN-LIST" not in cloud_payload
    assert "SECRET-IN-DICT" not in cloud_payload
    assert "SECRET-IN-NESTED-LIST" not in cloud_payload
    assert sent_knowledge[0].metadata == {"source": "internal", "labels": ["security"]}


@pytest.mark.asyncio
async def test_cloud_redacted_preserves_body_context_for_nested_pydantic_models(
    requirement_item: RequirementItem,
) -> None:
    """Fails if a Pydantic model below body loses the enclosing redaction context."""
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    knowledge = [
        KnowledgeChunkWithNestedBodies(
            chunk_id="chunk-4",
            project_id="p1",
            document_id="api.md",
            version=4,
            locator="Payloads#3",
            text="A separate secret body.",
            body=[
                NestedBodyPart(value="SECRET-IN-LIST-MODEL", identifier="BODY-LIST-ID"),
                {
                    "model": NestedBodyPart(
                        value="SECRET-IN-DICT-MODEL",
                        identifier="BODY-DICT-ID",
                    )
                },
            ],
            metadata={"identifier": "public-metadata-id", "owner": "operations"},
        )
    ]
    gateway = PolicyModelGateway(
        local_model=local,
        cloud_model=cloud,
        redactor=lambda value: "[REDACTED]",
    )

    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_REDACTED,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement_item,
        knowledge=knowledge,
    )

    sent_knowledge = cloud.await_args.kwargs["knowledge"]
    assert sent_knowledge == [
        KnowledgeChunkWithNestedBodies(
            chunk_id="chunk-4",
            project_id="p1",
            document_id="api.md",
            version=4,
            locator="Payloads#3",
            text="[REDACTED]",
            body=[
                NestedBodyPart(value="[REDACTED]", identifier="[REDACTED]"),
                {
                    "model": NestedBodyPart(
                        value="[REDACTED]",
                        identifier="[REDACTED]",
                    )
                },
            ],
            metadata={"identifier": "public-metadata-id", "owner": "operations"},
        )
    ]
    cloud_payload = repr(cloud.await_args.kwargs)
    assert "SECRET-IN-LIST-MODEL" not in cloud_payload
    assert "SECRET-IN-DICT-MODEL" not in cloud_payload
    assert sent_knowledge[0].chunk_id == "chunk-4"
    assert sent_knowledge[0].metadata == {
        "identifier": "public-metadata-id",
        "owner": "operations",
    }
