from __future__ import annotations

import pytest

from requirement_review.model_gateway.config import ModelProviderConfig
from requirement_review.model_gateway.factory import build_cloud_gateway
from requirement_review.model_gateway.openai_compatible import OpenAICompatibleClient


def test_build_minimax_cloud_gateway_from_config() -> None:
    config = ModelProviderConfig(
        provider="minimax",
        base_url="https://minimax.example/v1",
        model="MiniMax-M3",
        api_key="sk-minimax",
        timeout_s=11,
        max_retries=5,
        concurrency=2,
    )

    gateway = build_cloud_gateway(config)

    assert isinstance(gateway, OpenAICompatibleClient)
    assert gateway.base_url == "https://minimax.example/v1"
    assert gateway.model == "MiniMax-M3"
    assert gateway.api_key == "sk-minimax"
    assert gateway.timeout_s == 11
    assert gateway.max_retries == 5


def test_build_openai_compatible_cloud_gateway_from_config() -> None:
    config = ModelProviderConfig(
        provider="openai_compatible",
        base_url="https://llm.example/v1",
        model="provider-model",
        api_key="sk-provider",
        timeout_s=7,
        max_retries=1,
        concurrency=2,
    )

    gateway = build_cloud_gateway(config)

    assert isinstance(gateway, OpenAICompatibleClient)
    assert gateway.base_url == "https://llm.example/v1"
    assert gateway.model == "provider-model"
    assert gateway.api_key == "sk-provider"
    assert gateway.timeout_s == 7
    assert gateway.max_retries == 1


def test_unsupported_provider_is_rejected() -> None:
    config = ModelProviderConfig(
        provider="unknown",
        base_url="https://llm.example/v1",
        model="m",
        api_key="sk",
    )

    with pytest.raises(ValueError, match="unsupported model provider"):
        build_cloud_gateway(config)
