## Why

The backend currently treats the real model path as MiniMax-specific configuration, which makes adding OpenAI-compatible providers, Qwen, DeepSeek, or local backends harder than necessary. Recent real-review runs also showed that full-document review can create many upstream calls and fail opaquely when a provider rate-limits or returns malformed output.

This change introduces a provider-agnostic model gateway contract so the review workflow can select and operate multiple backend large-model providers safely, while preserving the existing MiniMax setup as a compatible path.

## What Changes

- Add provider-agnostic model runtime configuration using `REVIEW_MODEL_*` settings.
- Keep `MINIMAX_*` settings as backwards-compatible fallback for existing local deployments.
- Add provider selection for at least `minimax` and a generic `openai_compatible` provider.
- Normalize provider failures into safe internal error categories such as rate limit, timeout, upstream failure, authentication failure, bad response, and parse failure.
- Add configurable model-call concurrency and retry/backoff behavior to reduce burst failures during multi-dimension reviews.
- Improve review failure granularity so a single provider failure does not unnecessarily discard already valid results outside the failed model call scope.
- No **BREAKING** public HTTP API changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-contracts`: Clarify backend model-provider configuration, safe error handling, and review workflow resilience requirements that are shared by backend operation and future integrations.

## Non-goals

- Do not add a new frontend model-selection UI in this change.
- Do not add provider-specific native SDK dependencies unless the provider cannot be reached through the existing HTTP adapter shape.
- Do not change review approval, project isolation, authentication, or report publication semantics.
- Do not commit or expose provider credentials.

## Impact

- Affected code: backend model gateway configuration, provider registry/factory, model client error mapping, review workflow model-call execution, and backend tests.
- Affected contracts: root `public-contracts` gains requirements for model-provider selection, safe provider errors, and bounded upstream concurrency.
- Compatibility: existing MiniMax `.env` keys remain supported as fallback; deployments can migrate to `REVIEW_MODEL_*` incrementally.
- Dependencies: no required new runtime dependency is expected for the first implementation.
