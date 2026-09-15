# Frontend Agent Instructions

## Inheritance

All rules in the repository-root `AGENTS.md` apply here. The root `openspec/specs/` directory is authoritative for public contracts (HTTP API schemas, authentication and authorization, project isolation, shared domain models, error responses). This directory may only add frontend implementation constraints and must reference root contracts by repository-relative path (for example `openspec/specs/public-contracts/spec.md`).

If an implementation proposal would change a public contract (HTTP endpoint, shared schema, authorization rule, error shape), create or update the corresponding root OpenSpec change first; do not redefine contracts in this component.

## Frontend OpenSpec scope

- Put frontend-only specifications and changes under `frontend/openspec/`.
- Frontend topics include UI flows, routing, session context, client-side authorization gating, error surfacing, accessibility, build tooling, and frontend telemetry.
- Reference root contracts with repository-relative paths such as `openspec/specs/public-contracts/spec.md`.
- Run `openspec validate` from `frontend/` for component changes and from the repository root for any change that touches root contracts.

## Frontend engineering rules

- Use TypeScript with `strict` enabled. Mirror backend Pydantic models in `src/api/types.ts`; do not invent divergent field names.
- Keep network access behind a single typed API client module (`src/api/client.ts`). Every public request must inject the `X-User-ID`, `X-Project-ID`, and `X-Role` headers from the active session.
- Treat the session context as the only source of identity. Never read or store credentials outside the session store.
- Map backend errors to the stable error contract documented in the root `public-contracts` spec; do not leak stack traces or secrets to the UI.
- Hide UI affordances the active role cannot exercise (admin-only, reviewer-only). Do not rely on the client alone for authorization — the backend is authoritative.
- Idempotency keys for approval and finding-decision endpoints must be generated per user action and surfaced in the UI; reuse the same key on retry.
- Keep components functional and accessible (semantic HTML, keyboard navigable, label/control association, color-independent status).
- Use Vitest + React Testing Library for component and client tests. Update or add tests for every behavior change.
- Run `npm run lint`, `npm run typecheck`, and `npm test -- --run` from `frontend/` before completion.
- Use Conventional Commits. Do not commit `node_modules/`, `dist/`, coverage reports, or `.env` files.
