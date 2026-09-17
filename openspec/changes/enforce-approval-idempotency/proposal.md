## Why

The root public-contract capability `Human approval` already requires that "Approval and rejection operations SHALL be auditable and idempotent." However the in-memory backend runtime (`InMemoryApplicationServices.approve`) only forwards the `Idempotency-Key` header into the graph resume payload — it never compares a new request against a previously stored one for the same key. The `decide_finding` path enforces idempotency correctly, but `approve` does not.

End-to-end testing on the running backend confirmed the gap: sending two approval requests with the same `Idempotency-Key` but different bodies both return `202 Accepted`, both succeed, and both entries appear in the rendered report. This violates the public contract and means a retried-or-confused client can silently produce contradictory final decisions on a single review.

This change tightens the public-contract wording so "idempotent" has a testable interpretation, and patches the in-memory runtime to enforce that contract. It does not introduce a new persistence layer.

## What Changes

- Tighten the `Human approval` requirement to specify what idempotency means on `POST /api/v1/reviews/{review_id}/approval`:
  - A request that reuses an `Idempotency-Key` with the same body as the original MUST return the original outcome without re-executing the graph.
  - A request that reuses an `Idempotency-Key` with a different body MUST be rejected with a stable `409 idempotency_conflict` error that includes the key as correlation identifier.
- Make `InMemoryApplicationServices.approve` honor the same idempotency semantics as `decide_finding`: store the first (review_id, "approval", idempotency_key) tuple, replay identical bodies, and raise `IdempotencyConflictError` on body mismatch. The existing route handler already maps this exception to `409`.
- Add backend pytest coverage that fails before the implementation and passes after.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-contracts`: Sharpen the `Human approval` requirement so the idempotency clause on the approval endpoint is concretely testable (same body replay vs. same key + different body conflict).

## Non-goals

- No change to the approval graph semantics, the human-approval gate, or the report renderer.
- No change to authentication, authorization, project isolation, evidence traceability, or error contract wording.
- No new persistence layer, no migration. The in-memory adapter must become correct first; the future Postgres-backed adapter must inherit the same idempotency semantics.
- No frontend change in this proposal.
- Do not change the `Idempotency-Key` requirements on `decide_finding`; that path is already correct.

## Impact

- Affected code: `backend/src/requirement_review/api/runtime.py` (`approve` method) and `backend/tests/integration/test_review_lifecycle.py` (new idempotency cases). The route handler in `api/routes/reviews.py` already translates `IdempotencyConflictError` to `409`, so no change is required there.
- Affected contracts: root `public-contracts` `Human approval` requirement gains a normative clarification.
- Compatibility: this is a bug fix; the previous behavior was inconsistent with the documented contract. The new behavior makes the contract enforceable for clients that already send `Idempotency-Key`.
- Dependencies: none.
