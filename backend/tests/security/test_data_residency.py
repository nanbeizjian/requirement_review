from unittest.mock import AsyncMock

import pytest

from requirement_review.domain.models import (
    DataPolicy,
    EvidenceRef,
    RequirementItem,
    ReviewDimension,
)
from requirement_review.models.gateway import PolicyModelGateway


@pytest.mark.asyncio
async def test_local_only_payload_never_reaches_cloud() -> None:
    local = AsyncMock(return_value=[])
    cloud = AsyncMock(return_value=[])
    gateway = PolicyModelGateway(
        local_model=local, cloud_model=cloud, redactor=lambda value: "X"
    )
    requirement = RequirementItem(
        requirement_id="REQ-001",
        text="SECRET",
        evidence=EvidenceRef(
            source_type="requirement",
            document_id="d",
            version=1,
            locator="root#p1",
            quote="SECRET",
        ),
    )
    await gateway.review(
        project_id="p1",
        data_policy=DataPolicy.LOCAL_ONLY,
        dimension=ReviewDimension.SECURITY,
        requirement=requirement,
        knowledge=[],
    )
    cloud.assert_not_awaited()
