## Why

The backend's default runtime is `InMemoryApplicationServices` (a process-local dict).
End-to-end testing on 2026-09-17 showed that restarting uvicorn wipes every project,
review, finding, decision, and report. The `persistence/` package, `alembic`
migration, and `Settings.database_url` (REVIEW_DATABASE_URL via env_prefix) were
already implemented, but `app.create_app()` always constructed the in-memory
runtime. There was no working wiring between the configured DB and the API.

This change introduces `DatabaseApplicationServices`, an opt-in adapter that
satisfies the same `ApplicationServices` Protocol as `InMemoryApplicationServices`,
persists durable state to PostgreSQL, and keeps the existing in-memory runtime
as the default for tests and local dev when no DB is configured.

## What Changes

- New module `backend/src/requirement_review/api/db_runtime.py` with
  `DatabaseApplicationServices` implementing all 11 Protocol methods. State
  stored in PostgreSQL via SQLAlchemy 2.0 async sessions.
- `backend/src/requirement_review/api/app.py` extended so that when
  `REQUIREMENT_REVIEW_USE_DATABASE=1` is set AND `REVIEW_DATABASE_URL` is
  configured, the in-memory services are promoted to the DB adapter at app
  construction time. The promotion only applies to the default
  `create_app()` path; tests that pass `InMemoryApplicationServices()`
  explicitly get to keep it unless they opt in.
- The LangGraph handle for each review still lives in process memory; the
  durable record (run / findings / decisions / approvals / report) is
  written to PostgreSQL. Restarting the process loses the in-memory graph
  handle but preserves the historical record so list / detail / report /
  finding queries keep working.
- Idempotency semantics for `decide_finding` and `approve` are preserved
  via the existing `UniqueConstraint` clauses (`finding_id +
  idempotency_key` on `finding_decisions`, `review_id + idempotency_key`
  on `report_approvals`); the same `IdempotencyConflictError` →
  409 idempotency_conflict contract holds.
- Approval preconditions (every finding accept/reject or zero findings)
  are checked before resuming the graph, identical to the in-memory
  runtime. `PreconditionFailedError` → 409 approval_blocked_undecided.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-contracts`: No contract change. The HTTP shape stays the same;
  the storage backend changes transparently.

## Non-goals

- No migration to a Postgres-native LangGraph checkpointer (e.g.
  `langgraph-checkpoint-postgres`). The graph still uses `InMemorySaver`
  per process; durability is provided by the application tables, not by
  the LangGraph checkpoint store.
- No MinIO / object-store adapter in this change. Knowledge bytes are
  stored as a single `document_chunks` row (text column) so the schema
  keeps working without an S3-compatible service.
- No multi-process coordination. Two uvicorn workers writing to the same
  project will see last-writer-wins on identical rows; the schema is not
  designed for high concurrency. Acceptable for the current dev / single-
  worker scope.
- No change to the in-memory runtime contract or to the API route layer.
- No frontend change.

## Impact

- Affected code: `backend/src/requirement_review/api/db_runtime.py` (new,
  ~570 lines), `backend/src/requirement_review/api/app.py` (gated branch),
  `backend/src/requirement_review/persistence/tables.py` (read-only,
  used as-is), `backend/alembic/versions/0001_initial.py` (already
  present).
- Affected contracts: none (HTTP shape unchanged).
- Compatibility: zero impact when `REQUIREMENT_REVIEW_USE_DATABASE` is
  unset; tests that hard-code `InMemoryApplicationServices()` keep
  passing.
- Dependencies: `psycopg2-binary` was added to the venv (required by
  alembic when running migrations from the host against the local Docker
  Postgres). `asyncpg` was already present.
