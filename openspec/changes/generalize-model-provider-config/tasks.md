## 1. Configuration Contract

- [x] 1.1 Add backend tests for `REVIEW_MODEL_*` precedence over `MINIMAX_*` fallback and verify the new tests fail before implementation.
- [x] 1.2 Implement provider-agnostic model config loading with MiniMax fallback compatibility and verify the targeted config tests pass.
- [x] 1.3 Update backend documentation with generic model config examples and verify the README describes both generic settings and MiniMax fallback.

## 2. Provider Registry and Safe Errors

- [x] 2.1 Add backend tests for selecting `minimax` and `openai_compatible` providers from config and verify they fail before implementation.
- [x] 2.2 Implement a provider factory or registry that builds the configured real model gateway and verify provider-selection tests pass.
- [x] 2.3 Add backend tests for safe error categories covering 429, timeout, auth failure, 5xx, invalid JSON, and unparseable model content; verify they fail before implementation.
- [x] 2.4 Implement typed model-provider error categories without exposing credentials or document text and verify gateway error tests pass.

## 3. Concurrency, Retry, and Partial Success

- [x] 3.1 Add backend tests proving configured model-call concurrency limits simultaneous upstream calls and verify they fail before implementation.
- [x] 3.2 Implement bounded model-call concurrency for real provider calls and verify the concurrency tests pass.
- [x] 3.3 Add backend tests proving retry/backoff handles 429 and transient 5xx within configured retry limits and verify they fail before implementation.
- [x] 3.4 Implement bounded retry/backoff behavior and verify retry tests pass.
- [x] 3.5 Add backend workflow tests proving one failed requirement-level model call preserves unrelated valid findings while marking the affected dimension failed, and verify they fail before implementation.
- [x] 3.6 Implement requirement-level partial-success handling in review workflow and verify workflow tests pass.

## 4. Validation

- [x] 4.1 Run backend unit and integration tests affected by model gateway and review workflow changes and verify they pass.
- [x] 4.2 Run `openspec validate generalize-model-provider-config --strict` from the repository root and verify it passes.
- [x] 4.3 Start the backend with existing MiniMax fallback settings and verify startup still selects the real model gateway without exposing secrets.
