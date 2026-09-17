## Context

The repository already ships a Postgres persistence layer:
- `backend/src/requirement_review/persistence/tables.py` defines the
  SQLAlchemy 2.0 schema for projects, source_documents, document_chunks,
  requirement_items, review_runs, review_findings, finding_decisions,
  report_approvals, review_reports, audit_events, plus a project_members
  join table.
- `backend/src/requirement_review/persistence/repositories.py` provides
  `ReviewRepository` with `create`, `get_for_project`,
  `record_finding_decision`, `publish_report`, `replace_report`.
- `backend/src/requirement_review/persistence/db.py` builds an async
  session factory via `create_session_factory(settings)`.
- `backend/alembic/versions/0001_initial.py` calls `Base.metadata.create_all`.
- `backend/src/requirement_review/config.py` reads `REVIEW_DATABASE_URL`
  via pydantic-settings `env_prefix="REVIEW_"`.

What was missing: `app.create_app()` always constructed
`InMemoryApplicationServices()`. There was no path from the configured
DB URL to a working adapter.

## Goals / Non-Goals

**Goals:**
- New `DatabaseApplicationServices` class that satisfies the
  `ApplicationServices` Protocol, persists state to PostgreSQL, and
  reuses the existing LangGraph + `InMemorySaver` for graph execution.
- Wire it in `app.create_app()` behind a single env-var opt-in
  (`REQUIREMENT_REVIEW_USE_DATABASE=1`) so the in-memory runtime stays
  the default and existing tests are not affected.
- Preserve every public-contract idempotency / precondition behavior
  (`IdempotencyConflictError` → 409,
  `PreconditionFailedError` → 409 approval_blocked_undecided).
- Demonstrate end-to-end persistence by killing and restarting uvicorn
  and confirming the historical review is still queryable.

**Non-Goals:**
- No Postgres-native LangGraph checkpointer. The graph remains in
  memory per process; durability comes from the application tables.
- No object-store adapter; knowledge bytes go into `document_chunks.text`.
- No multi-process coordination.
- No change to the route layer or the HTTP shape.

## Decisions

### Promote InMemoryApplicationServices in place rather than refactor

`create_app()` already builds an `InMemoryApplicationServices` for both the
empty-gateway and real-model code paths. Adding a single post-construction
branch that swaps it for `DatabaseApplicationServices` keeps the rest of
the bootstrap untouched. The swap only happens when the caller didn't
inject a custom services object AND the env-var opt-in is set, so unit
tests that pass `InMemoryApplicationServices()` explicitly keep working.

Alternative considered: factory function `make_services()` returning
either adapter based on env. Rejected because it would force every test
that does `create_app(InMemoryApplicationServices())` to also set the env
flag or get wrapped into DB.

### Per-request session_scope, not module-level session

Each method opens `async with self.session_factory() as session:` and
relies on `expire_on_commit=False` so attribute access after `commit()`
keeps working. This avoids connection leaks across requests and keeps
the adapter stateless across uvicorn workers.

Alternative considered: long-lived session per app instance. Rejected
because it would force careful transaction management around concurrent
requests and complicate graceful shutdown.

### Graph handle in `self.reviews`, durable record in DB

The LangGraph + `InMemorySaver` handle is stored in `self.reviews: dict[str, ReviewRecord]`
on the adapter instance (same as the in-memory runtime). The graph's
post-invoke state is persisted to `review_runs`, `review_findings`,
`finding_decisions`, `report_approvals`, `review_reports` tables.
Restarting the process loses the graph handle but the durable record
survives, so read paths (`GET /reviews`, `GET /reviews/{id}`,
`GET /reports/{id}`, `GET /findings`) keep returning correct data.
Approval after restart returns 404 because the graph is gone — a
documented limitation, consistent with the in-memory runtime's behavior
when a record is missing.

Alternative considered: install `langgraph-checkpoint-postgres` and
store the graph in DB. Rejected as scope creep for this change; can
be added later without changing the public contract.

### Idempotency via DB constraints, not in-memory dict

The in-memory runtime keeps `self.decisions` and `self.approvals_by_key`
dicts for idempotency. The DB adapter instead relies on the existing
`UniqueConstraint("finding_id", "idempotency_key")` on
`finding_decisions` and `UniqueConstraint("review_id", "idempotency_key")`
on `report_approvals`. On `IntegrityError`, the adapter re-reads the
existing row and either replays the response (same body) or raises
`IdempotencyConflictError` (different body). The route layer maps this
to `409 idempotency_conflict` exactly as before.

Alternative considered: keep an in-memory dict for idempotency and only
use DB for the durable record. Rejected because it would lose
idempotency guarantees across restart, defeating the whole point of
switching to DB.

### `REQUIREMENT_REVIEW_USE_DATABASE` opt-in

The flag is consumed by `app.py` and is independent of
`REVIEW_DATABASE_URL`. If the flag is set but `REVIEW_DATABASE_URL`
is empty, the app logs a warning and stays in-memory. This matches the
existing fail-fast semantics (`EmptyModelGateway` falls back when
`REVIEW_MODEL_BACKEND` is unknown).

## Risks / Trade-offs

- After a restart, approve / decide_finding on a previously-created
  review will 404 because the graph handle is gone. The durable record
  is preserved; only the ability to mutate the workflow state is lost.
  Acceptable for the current single-worker dev setup; can be fixed
  later with `langgraph-checkpoint-postgres`.
- `FindingDecisionTable` does not carry `review_id` directly. The
  adapter joins through `review_findings.id` to scope decisions to a
  review. Index on `review_findings.review_id` (already present) keeps
  this efficient.
- Per-row serialization is fine for this dev path but will not scale to
  hundreds of concurrent reviewers. Out of scope.
- `langgraph-checkpoint-postgres` would let the graph handle survive
  restart; not added in this change.

## Migration Plan

1. alembic migration already ran (`0001_initial`) during local
   development against the docker-compose Postgres on `localhost:5432`.
   No schema changes from this change.
2. Operators enable the adapter by setting
   `REQUIREMENT_REVIEW_USE_DATABASE=1` and confirming
   `REVIEW_DATABASE_URL` points at a reachable Postgres.
3. Rollback is a single env-var unset; the in-memory runtime takes over
   automatically.
