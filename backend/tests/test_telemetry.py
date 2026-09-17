"""Tests for telemetry helpers (LangSmith config + key masking)."""


import pytest

from requirement_review.telemetry import configure_langsmith, mask_api_key, masked_env


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "<absent>"),
        ("", "<absent>"),
        ("x", "<masked>"),
        ("abcd", "<masked>"),
        ("abcde", "abcd***"),
        ("lsv2_pt_short", "lsv2_pt_s...rt"),
        ("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", "lsv2_pt_0...b6"),
        ("sk-cp-synthetic-placeholder-for-mask-test", "sk-c***"),
    ],
)
def test_mask_api_key(value, expected):
    assert mask_api_key(value) == expected


def test_masked_env_returns_mask(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "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")
    out = masked_env("MINIMAX_API_KEY")
    assert "lsv2_pt_0...b6" in out
    assert "0880d6e357db40cc" not in out


def test_masked_env_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    assert masked_env("MINIMAX_API_KEY") == "<absent>"


def test_configure_langsmith_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert configure_langsmith() == "disabled"


def test_configure_langsmith_misconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    with pytest.warns(UserWarning, match="LANGCHAIN_API_KEY"):
        assert configure_langsmith() == "misconfigured"


def test_configure_langsmith_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_pt_abc123")
    assert configure_langsmith() == "enabled"
