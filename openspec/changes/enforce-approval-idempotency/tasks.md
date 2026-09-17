## 1. Public Contract Tightening

- [x] 1.1 Author the `MODIFIED Requirements` delta in `openspec/changes/enforce-approval-idempotency/specs/public-contracts/spec.md` and verify it focuses the Human-approval clause on the approval endpoint's Idempotency-Key contract.

## 2. Backend Idempotency Tests (write first)

- [x] 2.1 Add backend integration tests covering: identical-body replay returns the original outcome without re-executing the graph; same key + different body returns 409 `idempotency_conflict` with the key in the response; missing `Idempotency-Key` still returns 422; verify the new tests fail against the current implementation.
- [x] 2.2 Add a backend unit test that drives `InMemoryApplicationServices.approve` directly with two different bodies and asserts the second call raises `IdempotencyConflictError`; verify it fails against the current implementation.

## 3. Runtime Fix

- [x] 3.1 Implement approval dedupe in `InMemoryApplicationServices.approve`: store the first response under `(review_id, idempotency_key)`, replay identical bodies, raise `IdempotencyConflictError` on body mismatch. Verify the unit test from 2.2 and the integration tests from 2.1 all pass.
- [x] 3.2 Update the existing `tests/integration/test_review_lifecycle.py` happy-path test if needed to use a fresh `Idempotency-Key` and verify it still passes against the new behavior.

## 4. Validation

- [x] 4.1 Run `pytest -q` from `backend/` and verify the full backend suite passes (no regressions).
- [x] 4.2 Run `openspec validate enforce-approval-idempotency --strict` from the repository root and verify it passes.
- [x] 4.3 Restart the local backend with default empty-model settings, re-run the e2e lifecycle script, and verify step 8 (same key + different body) now returns 409 instead of 202 and the report contains only one approval entry.
