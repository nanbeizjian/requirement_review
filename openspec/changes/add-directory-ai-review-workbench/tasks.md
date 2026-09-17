## 1. Contract queries and persistence

- [ ] 1.1 Add failing API tests for optional `source_name`, project-scoped `GET /api/v1/reviews`, stable ordering, summary counts, and cross-project isolation; verify the new cases fail for the expected missing behavior.
- [ ] 1.2 Extend API schemas, routes, service protocol, and in-memory runtime for source metadata and review listing; verify targeted and existing API tests pass.
- [ ] 1.3 Add a forward Alembic migration for nullable review `source_name` and decision lookup indexes, update SQLAlchemy mappings/repositories, and verify upgrade SQL plus repository tests cover historical null values and project filtering.

## 2. Finding decision lifecycle

- [ ] 2.1 Add failing service/API tests for finding responses with nullable/latest decisions, including stable latest-decision selection; verify failures identify the absent projection.
- [ ] 2.2 Implement decision projection in the in-memory service and persistence repository and expose it through the existing findings array; verify new and existing findings tests pass.
- [ ] 2.3 Add failing tests for same-key/same-body idempotent retries and same-key/different-body conflicts at project, review, and finding scope; verify the conflict case fails before implementation.
- [ ] 2.4 Implement strict decision idempotency with audit preservation and the stable compatible conflict error; verify API, repository, and security tests pass.
- [ ] 2.5 Add failing lifecycle tests for rejecting document approval with undecided or `re-review` findings while allowing all-resolved and zero-finding reviews; implement the backend finalization gate and verify all lifecycle cases pass.

## 3. Root and backend validation

- [ ] 3.1 Run `openspec validate add-directory-ai-review-workbench --strict` from the repository root and fix all root change validation errors.
- [ ] 3.2 Run `pytest -q`, `ruff check src tests alembic`, `mypy --follow-imports=skip src`, and `alembic upgrade head --sql` from `backend/`; fix regressions and record successful outputs.
- [ ] 3.3 Run backend integration tests proving project isolation, review-list recovery, latest finding decisions, strict idempotency, final approval gating, and report availability.
