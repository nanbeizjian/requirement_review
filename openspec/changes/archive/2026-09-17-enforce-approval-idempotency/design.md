## Context

The `public-contracts` capability already states that approval and rejection operations must be "auditable and idempotent." The in-memory backend runtime, however, only validates the presence of the `Idempotency-Key` header at the FastAPI layer; once the request reaches `InMemoryApplicationServices.approve`, the key is mixed into the graph resume payload and otherwise discarded. The graph's `validate_approval` node does not perform dedupe.

Meanwhile, the sibling path `decide_finding` already implements idempotency correctly: it stores decisions in `self.decisions[(review_id, finding_id, idempotency_key)]` and raises `IdempotencyConflictError` when the same key is reused with a different body. The route handler in `api/routes/reviews.py` translates that exception to `409` with a stable `code: "idempotency_conflict"`.

End-to-end probing against the running backend (uvicorn + `InMemoryApplicationServices`) on 2026-09-16 showed three approval requests with the same `Idempotency-Key`, two of which had different bodies, all returned `202 Accepted`, and all three entries appeared in the rendered Markdown report. That contradicts the public contract.

## Goals / Non-Goals

**Goals:**

- Make `approve` enforce idempotency in the same shape as `decide_finding`: store the first outcome keyed by `(review_id, "approval", idempotency_key)`, replay identical bodies, and raise `IdempotencyConflictError` on body mismatch.
- Pin the public-contract wording so the idempotency clause is testable: identical body → replay, different body with same key → 409.
- Cover the new behavior with backend pytests that fail before the implementation.

**Non-Goals:**

- No new persistence layer; the future Postgres-backed adapter will inherit the same `(review_id, scope, idempotency_key)` semantics but is out of scope here.
- No change to the `decide_finding` path.
- No frontend changes.
- No change to the approval graph itself.

## Decisions

### Reuse `IdempotencyConflictError`

The exception type already exists in `api/runtime.py`, and the route handler `approve_review` already catches `IdempotencyConflictError` and renders a 409 with `code: "idempotency_conflict"`. Reusing it gives us 409 mapping for free and keeps the error contract identical to `decide_finding`.

Alternative considered: introduce a new exception type to distinguish approval vs. finding conflicts. Rejected — clients already have to handle `idempotency_conflict` from `decide_finding`, and a unified code simplifies client logic.

### Use `(review_id, "approval", idempotency_key)` as the dedupe key

`self.decisions` is keyed by `(review_id, finding_id, idempotency_key)`. Mixing approval decisions into the same dict would collide with `finding_id`. Instead, store approvals in a dedicated `self.approvals: dict[(review_id, idempotency_key), dict]` and key collisions stay isolated.

Alternative considered: serialize approvals into `self.decisions` with a synthetic finding_id like `"__approval__"`. Rejected — it leaks the synthetic value to other code paths and is harder to extend with new "scopes" later.

### Replay identical bodies without re-executing the graph

If the stored `(review_id, idempotency_key)` entry matches the incoming payload (`action`, `comment`, `dimensions`, `findings`) exactly, return the stored response dict (`{"review_id": ..., "status": ...}`) without invoking `record.graph.ainvoke(Command(resume=...))`. This avoids redundant graph resume work on retries, which is the point of idempotency.

Alternative considered: always re-run the graph but mark duplicates. Rejected — re-running the graph is wasteful and may produce inconsistent `approvals` list size / report rendering between two identical calls.

## Risks / Trade-offs

- The store key `self.approvals` grows with each unique `Idempotency-Key` per review. Acceptable: the in-memory adapter is development-only and is replaced by a DB-backed adapter in production. The DB-backed adapter must enforce a uniqueness constraint at the storage layer.
- Storing the response dict means the stored `status` reflects the status at the time of the original call (e.g. `COMPLETED`). A replay returns the same status, which is the desired behavior for idempotent retries.

## Migration Plan

1. Write failing pytests that cover identical-body replay, different-body 409, and missing-key 422 on `POST /api/v1/reviews/{review_id}/approval`.
2. Patch `InMemoryApplicationServices.approve` to consult `self.approvals` before resuming the graph; raise `IdempotencyConflictError` on body mismatch; replay the original outcome on body match.
3. Re-run the targeted pytests and the full backend test suite to confirm no regressions.
4. Run `openspec validate enforce-approval-idempotency --strict` from the repository root.

Rollback is a single-file revert of `runtime.py`; no DB migrations involved.
