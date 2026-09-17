from __future__ import annotations

from .config import ModelProviderConfig
from .errors import ModelGatewayConfigError
from .openai_compatible import OpenAICompatibleClient
from .resilience import ResilientModelGateway

_OPENAI_COMPATIBLE_PROVIDERS = {"minimax", "openai_compatible"}


def build_cloud_gateway(config: ModelProviderConfig) -> OpenAICompatibleClient:
    provider = config.provider.lower()
    if provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        raise ModelGatewayConfigError(f"unsupported model provider: {config.provider!r}")
    return OpenAICompatibleClient(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_s=config.timeout_s,
        max_retries=config.max_retries,
    )


def build_resilient_cloud_gateway(config: ModelProviderConfig) -> ResilientModelGateway:
    inner = build_cloud_gateway(config)
    inner.max_retries = 0
    return ResilientModelGateway(
        inner,
        concurrency=config.concurrency,
        max_retries=config.max_retries,
    )
