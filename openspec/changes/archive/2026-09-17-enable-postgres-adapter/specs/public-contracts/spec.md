## MODIFIED Requirements

### Requirement: Root contract authority

The repository-root `openspec/specs/` directory SHALL be the authoritative source for public contracts. Component specifications SHALL reference these contracts and SHALL NOT define conflicting copies.

The HTTP API surface SHALL be implemented by either an in-memory adapter (`InMemoryApplicationServices`) for local dev and tests, or a PostgreSQL-backed adapter (`DatabaseApplicationServices`) when `REQUIREMENT_REVIEW_USE_DATABASE=1` is set. Both adapters satisfy the same `ApplicationServices` Protocol and produce identical response bodies for every public endpoint.

#### Scenario: Backend consumes a public contract

- **WHEN** a backend change uses an HTTP schema, authorization rule, shared domain model, or error response
- **THEN** the backend specification references the applicable root contract
- **AND** any contract modification is proposed in the root OpenSpec store

#### Scenario: Adapter selection is transparent to clients

- **WHEN** a client issues an HTTP request to any `/api/v1/...` endpoint
- **THEN** the response shape, status codes, error contract, and idempotency semantics are identical regardless of whether the active adapter is in-memory or PostgreSQL-backed
- **AND** the only client-observable difference is durability across process restarts (DB adapter preserves history; in-memory adapter does not)
