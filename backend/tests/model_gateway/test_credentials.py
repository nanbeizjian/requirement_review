"""Credentials and configuration errors for OpenAICompatibleClient."""

from __future__ import annotations

import pytest

from requirement_review.model_gateway import (
    ModelGatewayConfigError,
    OpenAICompatibleClient,
)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_BASE_URL", raising=False)
    monkeypatch.delenv("MINIMAX_MODEL", raising=False)
    with pytest.raises(ModelGatewayConfigError) as exc:
        OpenAICompatibleClient()
    assert "MINIMAX_API_KEY" in str(exc.value)


def test_explicit_empty_api_key_still_raises() -> None:
    with pytest.raises(ModelGatewayConfigError):
        OpenAICompatibleClient(api_key="", require_api_key=True)


def test_explicit_key_with_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    client = OpenAICompatibleClient(api_key="sk-test-key", require_api_key=True)
    assert client.api_key == "sk-test-key"


def test_require_api_key_false_skips_env_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    client = OpenAICompatibleClient(require_api_key=False)
    assert client.api_key is None
