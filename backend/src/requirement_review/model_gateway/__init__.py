"""Backend model gateway capability.

Wraps an OpenAI-compatible HTTP client behind a `ModelGateway` protocol and
routes calls according to the root public contract's `data_policy`. See
`openspec/changes/add-real-llm-model-gateway/` for the spec, design, and tasks.
"""

from .config import ModelProviderConfig
from .errors import (
    ModelGatewayAuthError,
    ModelGatewayConfigError,
    ModelGatewayParseError,
    ModelGatewayRateLimitError,
    ModelGatewayResponseError,
    ModelGatewayTimeoutError,
    ModelGatewayTransientError,
)
from .openai_compatible import OpenAICompatibleClient
from .policy import PolicyModelGateway
from .redact import redact_payload

__all__ = [
    "ModelGatewayAuthError",
    "ModelGatewayConfigError",
    "ModelGatewayParseError",
    "ModelProviderConfig",
    "ModelGatewayRateLimitError",
    "ModelGatewayResponseError",
    "ModelGatewayTimeoutError",
    "ModelGatewayTransientError",
    "OpenAICompatibleClient",
    "PolicyModelGateway",
    "redact_payload",
]
