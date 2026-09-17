from __future__ import annotations

import asyncio

from .errors import ModelGatewayTransientError


class ResilientModelGateway:
    def __init__(
        self,
        inner,
        *,
        concurrency: int,
        max_retries: int,
        backoff_s: float = 0.25,
    ) -> None:
        self.inner = inner
        self.max_retries = max(0, max_retries)
        self.backoff_s = max(0.0, backoff_s)
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    async def review(self, **kwargs):
        async with self._semaphore:
            attempt = 0
            while True:
                try:
                    return await self.inner.review(**kwargs)
                except ModelGatewayTransientError:
                    if attempt >= self.max_retries:
                        raise
                    if self.backoff_s:
                        await asyncio.sleep(self.backoff_s * (2**attempt))
                    attempt += 1
