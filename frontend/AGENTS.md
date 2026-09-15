# Frontend Agent Instructions

## Inheritance

All rules in the repository-root `AGENTS.md` apply here. The root `openspec/specs/` directory is authoritative for public contracts. Frontend specifications SHALL reference root contracts and SHALL NOT duplicate HTTP API, authentication, authorization, project-isolation, shared-schema, or error contracts.

## Frontend OpenSpec scope

- Put frontend-only specifications and changes under `frontend/openspec/`.
- Frontend topics include UI flows, routing, client-side authorization gating, error surfacing, accessibility, build tooling, and frontend telemetry.
- Reference root contracts with repository-relative paths such as `openspec/specs/public-contracts/spec.md`.
- Run `openspec validate` from `frontend/` for component changes and from the repository root for changes that affect root contracts.

## Frontend engineering rules

- Use TypeScript with `strict` enabled and mirror approved backend schemas in typed API models.
- Keep network access behind one typed API client; inject identity headers from the active session.
- Treat the session context as the only source of identity and do not store credentials outside it.
- Hide actions unavailable to the active role while keeping the backend authoritative for authorization.
- Generate one idempotency key per user action and reuse it only for retrying that action.
- Keep components accessible and add Vitest plus React Testing Library coverage for behavior changes.
- Run lint, typecheck, tests, and production build before completion.

