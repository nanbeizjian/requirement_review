"""Covers requirement_review.telemetry.configure_langsmith env-var behavior."""

import os
import warnings
from collections.abc import Iterator

import pytest

from requirement_review.telemetry import configure_langsmith


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for var in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT", "LANGCHAIN_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_disabled_when_tracing_flag_absent(clean_env: None) -> None:
    assert configure_langsmith() == "disabled"


def test_disabled_when_tracing_flag_false(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    assert configure_langsmith() == "disabled"


def test_misconfigured_when_tracing_true_without_api_key(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    with pytest.warns(UserWarning, match="LANGCHAIN_API_KEY"):
        assert configure_langsmith() == "misconfigured"


def test_misconfigured_when_api_key_wrong_prefix(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "sk-not-a-langsmith-key")
    with pytest.warns(UserWarning, match="malformed"):
        assert configure_langsmith() == "misconfigured"


def test_enabled_with_valid_config(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_pt_abc123def456")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "requirement-review-staging")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no warnings on a valid config
        assert configure_langsmith() == "enabled"


def test_truthy_aliases_for_tracing_flag(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("true", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", value)
        monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_pt_x")
        assert configure_langsmith() == "enabled", value
