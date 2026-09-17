from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_MINIMAX_MODEL = "MiniMax-Text-01"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_CONCURRENCY = 2


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _float_env(name: str, default: float) -> float:
    value = _env(name)
    if value is None:
        return default
    return float(value)


def _int_env(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class ModelProviderConfig:
    provider: str
    base_url: str
    model: str
    api_key: str | None
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES
    concurrency: int = DEFAULT_CONCURRENCY

    @classmethod
    def from_env(cls) -> "ModelProviderConfig":
        provider = (_env("REVIEW_MODEL_PROVIDER") or "minimax").lower()
        if provider == "real":
            provider = "minimax"

        base_url = _env("REVIEW_MODEL_BASE_URL")
        model = _env("REVIEW_MODEL_NAME")
        api_key = _env("REVIEW_MODEL_API_KEY")

        if provider == "minimax":
            base_url = base_url or _env("MINIMAX_BASE_URL") or DEFAULT_MINIMAX_BASE_URL
            model = model or _env("MINIMAX_MODEL") or DEFAULT_MINIMAX_MODEL
            api_key = api_key or _env("MINIMAX_API_KEY")

        return cls(
            provider=provider,
            base_url=base_url or "",
            model=model or "",
            api_key=api_key,
            timeout_s=_float_env("REVIEW_MODEL_TIMEOUT_S", DEFAULT_TIMEOUT_S),
            max_retries=_int_env("REVIEW_MODEL_MAX_RETRIES", DEFAULT_MAX_RETRIES),
            concurrency=_int_env("REVIEW_MODEL_CONCURRENCY", DEFAULT_CONCURRENCY),
        )
