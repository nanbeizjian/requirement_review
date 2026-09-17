## Context

The backend currently has a real-model startup path that builds a `PolicyModelGateway` backed by `OpenAICompatibleClient`, with environment names centered on MiniMax. The review workflow fans out by dimension and then loops through requirement items, which can produce a large number of upstream calls for a single uploaded document. Provider errors are currently collapsed into broad review failures to avoid leaking document content.

See `proposal.md` for motivation and `specs/public-contracts/spec.md` for the behavior contract.

## Goals / Non-Goals

**Goals:**

- Introduce a provider-agnostic configuration layer with `REVIEW_MODEL_*` settings.
- Preserve current MiniMax behavior and `MINIMAX_*` fallback settings.
- Add a provider registry/factory that can select `minimax` and `openai_compatible` first, with a shape that can later add Qwen, DeepSeek, or local providers.
- Normalize model-provider exceptions into safe categories that can be logged and stored without leaking secrets or document text.
- Add bounded concurrency and retry/backoff around upstream model calls.
- Reduce failure blast radius so one failed model call does not clear unrelated successful findings.

**Non-Goals:**

- No frontend provider-selection UI.
- No change to public review API schemas beyond existing status/failure fields.
- No native provider SDK integration in the first pass.
- No credential migration requirement for local MiniMax users.

## Decisions

### Use generic config with provider-specific fallback

Add a backend config object that reads generic settings first:

- `REVIEW_MODEL_PROVIDER`
- `REVIEW_MODEL_BASE_URL`
- `REVIEW_MODEL_NAME`
- `REVIEW_MODEL_API_KEY`
- `REVIEW_MODEL_TIMEOUT_S`
- `REVIEW_MODEL_MAX_RETRIES`
- `REVIEW_MODEL_CONCURRENCY`

For `provider=minimax`, fall back to existing `MINIMAX_BASE_URL`, `MINIMAX_MODEL`, and `MINIMAX_API_KEY` when the generic values are absent. This keeps existing `.env` files working while allowing new providers to share the same shape.

Alternative considered: require immediate rename from `MINIMAX_*` to `REVIEW_MODEL_*`. Rejected because it creates avoidable local and deployment churn.

### Keep OpenAI-compatible HTTP as the first provider abstraction

Most target providers expose an OpenAI-compatible chat completions API or a close variant. The first implementation should keep a reusable `OpenAICompatibleClient` and select provider defaults through a small registry. Provider-specific adapters can be added only when request/response behavior diverges.

Alternative considered: create separate full clients for every provider immediately. Rejected as over-abstracted before provider-specific differences are proven.

### Normalize errors at the gateway boundary

The model gateway should raise typed errors with safe categories such as:

- `rate_limited`
- `timeout`
- `auth_failed`
- `upstream_unavailable`
- `bad_response`
- `parse_failed`
- `config_error`

The original provider response body must not be returned through public APIs. Logs may include safe category, provider name, status code, request correlation identifiers, and retry count, but not credentials or document body.

Alternative considered: continue collapsing all exceptions to `review_failed`. Rejected because it makes operations opaque and hides rate-limit behavior.

### Bound calls through a shared limiter

The real-model application service should wrap provider calls with an `asyncio.Semaphore` sized by `REVIEW_MODEL_CONCURRENCY`. This limits fan-out across dimensions and requirement items without changing the review graph contract.

Alternative considered: make the graph sequential by removing dimension fan-out. Rejected because it would be a larger workflow behavior change and would slow all successful cases.

### Keep partial successes

Within a dimension, each requirement review should be treated as its own model-call scope. If one requirement fails after retries, valid findings collected from other requirements in the same dimension should remain available. The dimension should still be listed in `failed_dimensions` when any scope failed.

Alternative considered: preserve current all-or-nothing dimension behavior. Rejected because it discards useful findings and exaggerates transient provider failures.

## Risks / Trade-offs

- Provider outputs may still be inconsistent across vendors -> keep schema normalization and evidence validation as the final gate.
- Partial success can produce reports with failed dimensions -> keep `failed_dimensions` visible so humans know review coverage is incomplete.
- Lower concurrency increases review latency -> make concurrency configurable and default conservatively for real providers.
- Generic config may hide provider-specific needs -> keep registry extensible and add provider-specific options only when a concrete provider requires them.

## Migration Plan

1. Add tests for generic config precedence and MiniMax fallback compatibility.
2. Add provider registry/factory and typed safe errors.
3. Add concurrency and retry/backoff tests around model calls.
4. Update review node behavior to preserve valid findings when one model-call scope fails.
5. Update backend docs with generic configuration and MiniMax fallback examples.

Rollback is straightforward: set only the existing `MINIMAX_*` values and use the MiniMax provider path, or unset the real backend selector to return to the empty development gateway.
