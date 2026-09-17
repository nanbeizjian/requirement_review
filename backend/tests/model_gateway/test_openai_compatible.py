"""Integration-style tests for OpenAICompatibleClient using httpx.MockTransport."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from requirement_review.domain.models import (
    DataPolicy,
    EvidenceRef,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
)
from requirement_review.model_gateway import (
    ModelGatewayResponseError,
    ModelGatewayTransientError,
    OpenAICompatibleClient,
)


def _requirement(text: str = "用户应该可以登录", rid: str = "r1") -> RequirementItem:
    return RequirementItem(
        requirement_id=rid,
        text=text,
        evidence=EvidenceRef(
            source_type="requirement",
            document_id="d1",
            version=1,
            locator="L1",
            quote=text,
        ),
    )


def _knowledge(text: str = "历史背景: alice@example.com") -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            chunk_id="k1",
            project_id="p1",
            document_id="d1",
            version=1,
            locator="L2",
            text=text,
        )
    ]


def _ok_response(findings: list[dict[str, Any]]) -> httpx.Response:
    body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"findings": findings}, ensure_ascii=False)
                }
            }
        ]
    }
    return httpx.Response(200, json=body)


def _finding_payload() -> dict[str, Any]:
    return {
        "requirement_id": "r1",
        "dimension": "completeness",
        "severity": "high",
        "issue": "缺少边界条件",
        "impact": "可能误删数据",
        "recommendation": "补充空值校验",
        "confidence": 0.9,
        "evidence": [
            {
                "source_type": "requirement",
                "document_id": "d1",
                "version": 1,
                "locator": "L1",
                "quote": "用户应该可以登录",
            }
        ],
        "uses_system_fact": False,
    }


async def _post_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/chat/completions"):
        return _ok_response([_finding_payload()])
    return httpx.Response(404, json={"detail": "not found"})


def _make_client(handler) -> OpenAICompatibleClient:
    transport = httpx.MockTransport(handler)
    return OpenAICompatibleClient(
        api_key="sk-test",
        base_url="https://example.test/v1",
        model="m-test",
        timeout_s=5.0,
        max_retries=2,
        transport=transport,
    )


@pytest.mark.asyncio
async def test_review_success_returns_findings() -> None:
    client = _make_client(_post_handler)
    out = await client.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_ALLOWED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=_requirement(),
        knowledge=_knowledge(),
    )
    assert len(out) == 1
    assert out[0].requirement_id == "r1"


@pytest.mark.asyncio
async def test_review_redacts_payload_when_policy_requires() -> None:
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return _ok_response([])

    client = _make_client(handler)
    await client.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_REDACTED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=_requirement(text="联系 alice@example.com", rid="r2"),
        knowledge=_knowledge(text="phone 13800001234"),
    )
    body_str = json.dumps(captured["body"], ensure_ascii=False)
    assert "alice@example.com" not in body_str
    assert "13800001234" not in body_str
    assert "<email>" in body_str
    assert "<phone>" in body_str


@pytest.mark.asyncio
async def test_review_sends_auth_header() -> None:
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return _ok_response([])

    client = _make_client(handler)
    await client.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_ALLOWED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=_requirement(),
        knowledge=[],
    )
    assert captured["auth"] == "Bearer sk-test"


@pytest.mark.asyncio
async def test_review_retries_on_429() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"detail": "rate limited"})
        return _ok_response([])

    client = _make_client(handler)
    await client.review(
        project_id="p1",
        data_policy=DataPolicy.CLOUD_ALLOWED,
        dimension=ReviewDimension.COMPLETENESS,
        requirement=_requirement(),
        knowledge=[],
    )
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_review_exhausts_retries_then_raises() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"detail": "down"})

    client = _make_client(handler)
    with pytest.raises(ModelGatewayTransientError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "upstream_unavailable"
    assert calls["n"] >= 3


@pytest.mark.asyncio
async def test_review_401_auth_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad"})

    client = _make_client(handler)
    with pytest.raises(ModelGatewayTransientError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "auth_failed"


@pytest.mark.asyncio
async def test_review_429_raises_safe_rate_limit_category() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "secret document text"})

    client = OpenAICompatibleClient(
        api_key="sk-test",
        base_url="https://example.test/v1",
        model="m-test",
        timeout_s=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ModelGatewayTransientError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "rate_limited"
    assert "secret document text" not in str(exc.value)


@pytest.mark.asyncio
async def test_review_timeout_raises_safe_timeout_category() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("secret document text")

    client = OpenAICompatibleClient(
        api_key="sk-test",
        base_url="https://example.test/v1",
        model="m-test",
        timeout_s=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ModelGatewayTransientError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "timeout"
    assert "secret document text" not in str(exc.value)


@pytest.mark.asyncio
async def test_review_invalid_json_raises_safe_bad_response_category() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    client = _make_client(handler)
    with pytest.raises(ModelGatewayResponseError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "bad_response"


@pytest.mark.asyncio
async def test_review_unparseable_model_content_raises_parse_failed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json at all"}}]},
        )

    client = _make_client(handler)
    with pytest.raises(ModelGatewayResponseError) as exc:
        await client.review(
            project_id="p1",
            data_policy=DataPolicy.CLOUD_ALLOWED,
            dimension=ReviewDimension.COMPLETENESS,
            requirement=_requirement(),
            knowledge=[],
        )
    assert exc.value.category == "parse_failed"
