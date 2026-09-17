## 1. Persistence adapter

- [x] 1.1 Add `DatabaseApplicationServices` class in `backend/src/requirement_review/api/db_runtime.py` satisfying the `ApplicationServices` Protocol (create_project, add_knowledge, reindex, create_review, get_review, list_reviews, get_findings, decide_finding, approve, get_report). Use `async_sessionmaker` per `db.create_session_factory(settings)`. Verify the new module imports cleanly and `ast.parse` succeeds.
- [x] 1.2 Preserve every public-contract behavior of the in-memory runtime: Idempotency-Key replay / 409 on `approve` and `decide_finding`; PreconditionFailedError when not all findings accept/reject; report only renders after `status == COMPLETED`; cross-project 404 on every project-scoped method.

## 2. App wiring

- [x] 2.1 In `backend/src/requirement_review/api/app.py`, gate the in-memory → DB promotion behind `REQUIREMENT_REVIEW_USE_DATABASE=1`. Tests that explicitly pass `InMemoryApplicationServices()` keep using it unless they opt in. Add a structured log line when the adapter is selected.
- [x] 2.2 Document the new env var in `.env` and add it to `.env.example`. Document the migration step (`alembic upgrade head`) and the env-var combination needed to enable the adapter.

## 3. Persistence end-to-end

- [x] 3.1 Run `alembic upgrade head` against the docker-compose Postgres on `localhost:5432`. Verify `Base.metadata.create_all` produced all 12 tables (`projects`, `source_documents`, `document_chunks`, `requirement_items`, `review_runs`, `review_findings`, `finding_decisions`, `report_approvals`, `review_reports`, `audit_events`, `project_members`, `alembic_version`).
- [x] 3.2 Create a project + review + approval through the HTTP API with `REQUIREMENT_REVIEW_USE_DATABASE=1` set. Confirm rows in `projects`, `review_runs`, `report_approvals`, `review_reports`. Confirm the rendered report body matches the in-memory runtime's output.
- [x] 3.3 Kill uvicorn, restart with the same `.env`, and confirm the prior review is still queryable through `GET /reviews/{id}`, `GET /reviews/{id}/report`, and `GET /reviews` (list). Document that approve / decide_finding on a previously-created review returns 404 because the LangGraph handle is process-local.

## 4. Tests

- [x] 4.1 Add `backend/tests/integration/test_db_adapter.py` covering the DB-backed services end-to-end: create_project → add_knowledge → create_review → get_review (status PENDING → WAITING_APPROVAL) → approve → get_report. Verify the rows exist in PostgreSQL after each step. Verify idempotency: same key + same body returns the original outcome; same key + different body raises IdempotencyConflictError.
- [x] 4.2 Run `pytest -q` from `backend/` and confirm the full suite passes with no regressions. The existing in-memory tests must keep passing because the opt-in flag is not set in the test environment.

## 5. Validation

- [x] 5.1 Run `openspec validate enable-postgres-adapter --strict` from the repository root and verify it passes.
- [x] 5.2 Start the backend with `REQUIREMENT_REVIEW_USE_DATABASE=1` and the docker-compose Postgres, create a review, kill uvicorn, restart, and confirm the review is still queryable through the API.
