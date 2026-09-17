from __future__ import annotations

import pytest

from requirement_review.model_gateway.config import ModelProviderConfig


def _clear_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "REVIEW_MODEL_PROVIDER",
        "REVIEW_MODEL_BASE_URL",
        "REVIEW_MODEL_NAME",
        "REVIEW_MODEL_API_KEY",
        "REVIEW_MODEL_TIMEOUT_S",
        "REVIEW_MODEL_MAX_RETRIES",
        "REVIEW_MODEL_CONCURRENCY",
        "MINIMAX_BASE_URL",
        "MINIMAX_MODEL",
        "MINIMAX_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_review_model_settings_take_precedence_over_minimax_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("REVIEW_MODEL_PROVIDER", "openai_compatible")
    monkeypatch.setenv("REVIEW_MODEL_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("REVIEW_MODEL_NAME", "generic-model")
    monkeypatch.setenv("REVIEW_MODEL_API_KEY", "generic-key")
    monkeypatch.setenv("REVIEW_MODEL_TIMEOUT_S", "12.5")
    monkeypatch.setenv("REVIEW_MODEL_MAX_RETRIES", "4")
    monkeypatch.setenv("REVIEW_MODEL_CONCURRENCY", "3")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setenv("MINIMAX_MODEL", "minimax-model")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")

    config = ModelProviderConfig.from_env()

    assert config.provider == "openai_compatible"
    assert config.base_url == "https://generic.example/v1"
    assert config.model == "generic-model"
    assert config.api_key == "generic-key"
    assert config.timeout_s == 12.5
    assert config.max_retries == 4
    assert config.concurrency == 3


def test_minimax_settings_are_used_as_backwards_compatible_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setenv("MINIMAX_MODEL", "MiniMax-M3")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")

    config = ModelProviderConfig.from_env()

    assert config.provider == "minimax"
    assert config.base_url == "https://minimax.example/v1"
    assert config.model == "MiniMax-M3"
    assert config.api_key == "minimax-key"
