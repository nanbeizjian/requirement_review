from __future__ import annotations

import asyncio

import pytest

from requirement_review.model_gateway import (
    ModelGatewayRateLimitError,
    ModelGatewayTransientError,
)
from requirement_review.model_gateway.resilience import ResilientModelGateway


@pytest.mark.asyncio
async def test_resilient_gateway_limits_concurrent_calls() -> None:
    active = 0
    max_active = 0

    class SlowGateway:
        async def review(self, **kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return []

    gateway = ResilientModelGateway(SlowGateway(), concurrency=2, max_retries=0)

    await asyncio.gather(*(gateway.review(project_id="p") for _ in range(8)))

    assert max_active == 2


@pytest.mark.asyncio
async def test_resilient_gateway_retries_rate_limit_then_succeeds() -> None:
    calls = 0

    class FlakyGateway:
        async def review(self, **kwargs):
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ModelGatewayRateLimitError("safe")
            return ["ok"]

    gateway = ResilientModelGateway(
        FlakyGateway(), concurrency=1, max_retries=3, backoff_s=0
    )

    assert await gateway.review(project_id="p") == ["ok"]
    assert calls == 3


@pytest.mark.asyncio
async def test_resilient_gateway_stops_after_retry_limit() -> None:
    calls = 0

    class DownGateway:
        async def review(self, **kwargs):
            nonlocal calls
            calls += 1
            raise ModelGatewayTransientError("safe")

    gateway = ResilientModelGateway(
        DownGateway(), concurrency=1, max_retries=2, backoff_s=0
    )

    with pytest.raises(ModelGatewayTransientError):
        await gateway.review(project_id="p")
    assert calls == 3
