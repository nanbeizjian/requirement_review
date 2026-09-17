"""Tests for PolicyModelGateway routing per data_policy."""

from __future__ import annotations

from typing import Any

import pytest

from requirement_review.domain.models import (
    DataPolicy,
    EvidenceRef,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
)
from requirement_review.model_gateway import (
    ModelGatewayConfigError,
    PolicyModelGateway,
)


class FakeGateway:
    def __init__(self, label: str) -> None:
        self.label = label
        self.calls = 0
        self.last_kwargs: dict[str, Any] = {}

    async def review(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return [f"{self.label}-finding"]


@pytest.fixture
def req() -> RequirementItem:
    return RequirementItem(
        requirement_id="r1",
        text="t",
        evidence=EvidenceRef(source_type="requirement", document_id="d1", version=1, locator="L1", quote="t"),
    )


@pytest.fixture
def kc() -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id="k1",
        project_id="p1",
        document_id="d1",
        version=1,
        locator="L2",
        text="ctx",
    )


@pytest.mark.asyncio
async def test_local_only_routes_to_local(req, kc):
    local, cloud = FakeGateway("local"), FakeGateway("cloud")
    gw = PolicyModelGateway(local=local, cloud=cloud)
    out = await gw.review(
        project_id="p1",
        data_policy=DataPolicy.LOCAL_ONLY,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=req,
        knowledge=[kc],
    )
    assert out == ["local-finding"]
    assert local.calls == 1
    assert cloud.calls == 0
    assert local.last_kwargs["data_policy"] == DataPolicy.LOCAL_ONLY


@pytest.mark.asyncio
async def test_cloud_allowed_routes_to_cloud(req, kc):
    local, cloud = FakeGateway("local"), FakeGateway("cloud")
    gw = PolicyModelGateway(local=local, cloud=cloud)
    out = await gw.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_ALLOWED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=req,
        knowledge=[kc],
    )
    assert out == ["cloud-finding"]
    assert local.calls == 0
    assert cloud.calls == 1
    assert cloud.last_kwargs["data_policy"] == DataPolicy.CLOUD_ALLOWED


@pytest.mark.asyncio
async def test_cloud_redacted_routes_to_cloud(req, kc):
    local, cloud = FakeGateway("local"), FakeGateway("cloud")
    gw = PolicyModelGateway(local=local, cloud=cloud)
    await gw.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_REDACTED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=req,
        knowledge=[kc],
    )
    assert cloud.last_kwargs["data_policy"] == DataPolicy.CLOUD_REDACTED


@pytest.mark.asyncio
async def test_missing_gateways_raise():
    with pytest.raises(ModelGatewayConfigError):
        PolicyModelGateway(local=None, cloud=None)
    with pytest.raises(ModelGatewayConfigError):
        PolicyModelGateway(local=FakeGateway("l"), cloud=None)
    with pytest.raises(ModelGatewayConfigError):
        PolicyModelGateway(local=None, cloud=FakeGateway("c"))


@pytest.mark.asyncio
async def test_unsupported_policy_raises(req, kc):
    gw = PolicyModelGateway(local=FakeGateway("l"), cloud=FakeGateway("c"))
    with pytest.raises(ModelGatewayConfigError):
        await gw.review(
            project_id="p1",
            data_policy="bogus",
            dimension=ReviewDimension.COMPLETENESS,
            requirement=req,
            knowledge=[kc],
        )
