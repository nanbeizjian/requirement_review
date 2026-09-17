"""Exceptions raised by the model gateway capability."""


class ModelGatewayError(Exception):
    """Base class for all model gateway errors."""

    category = "model_gateway_error"

    def __init__(self, message: str | None = None, *, status_code: int | None = None):
        super().__init__(message or self.category)
        self.status_code = status_code


class ModelGatewayConfigError(ModelGatewayError, ValueError):
    """Raised when the gateway cannot start because configuration is invalid.

    Examples: missing required environment variable, conflicting options,
    a `data_policy` value the gateway does not recognise.
    """

    category = "config_error"


class ModelGatewayTransientError(ModelGatewayError):
    """Raised for retryable upstream problems: timeout, 5xx, 429.

    Surfaced to callers as a single-dimension failure so other dimensions can
    continue. The full report state transitions to FAILED only if every
    dimension fails (handled in the LangGraph node, not here).
    """

    category = "upstream_unavailable"


class ModelGatewayRateLimitError(ModelGatewayTransientError):
    """Raised when an upstream provider rate-limits a model call."""

    category = "rate_limited"


class ModelGatewayTimeoutError(ModelGatewayTransientError):
    """Raised when an upstream provider times out."""

    category = "timeout"


class ModelGatewayAuthError(ModelGatewayTransientError):
    """Raised when provider credentials are missing, invalid, or forbidden."""

    category = "auth_failed"


class ModelGatewayResponseError(ModelGatewayError):
    """Raised when a provider returns unusable or invalid response content."""

    category = "bad_response"


class ModelGatewayParseError(ModelGatewayResponseError):
    """Raised when model content cannot be parsed as review findings."""

    category = "parse_failed"
