## Context

The backend is complete: FastAPI exposes the public HTTP API described in `openspec/specs/public-contracts/spec.md`, plus backend-specific implementations for LangGraph, knowledge retrieval, persistence, and reporting. The repository has a root OpenSpec store and a `backend/openspec/` component store, both driven by the spec-driven workflow.

There is no client. Anyone wanting to use the system must `curl` the backend. This change adds a typed, role-aware web UI while preserving the separation between backend and frontend and without modifying the root public contracts.

## Goals / Non-Goals

**Goals:**
- Provide a single-page web UI covering projects, knowledge, reviews, findings, approval, and report.
- Consume, not redefine, the root public contract surface.
- Mirror backend Pydantic field names exactly.
- Enforce session and role context in the UI; rely on the backend for authorization.
- Map every backend error to the stable error contract.
- Establish a frontend OpenSpec store that follows the same conventions as the backend store.
- Provide unit tests for the typed client and (where practical) the error surface.

**Non-Goals:**
- Authentication, SSO, OAuth, token issuance, or any secret-bearing identity provider integration.
- Editing or weakening the root public-contract spec.
- Production deployment pipeline for the frontend (Docker image, hosting config).
- Real-time updates (SSE, websockets).
- A no-JS fallback or native mobile shell.

## Decisions

### 1. React 18 + TypeScript + Vite
Chosen for the smallest credible production-grade stack that matches the repo's modern conventions. Vite gives a fast dev server and a single `vite build` output that the backend can serve later via static mount in a follow-up change. TypeScript with `strict: true` enforces the same discipline backend uses with Pydantic.

### 2. One typed client module, no third-party HTTP library
A hand-written `RequirementReviewClient` wraps `fetch` and centralizes header injection, error decoding, and `Idempotency-Key` handling. Adding `axios`/`ky`/`openapi-fetch` would require either duplicating the OpenAPI schema or pulling codegen tooling in. For the surface area we need, native `fetch` is enough.

### 3. React Router with a small set of routes
The user journeys are well-defined (projects → knowledge → reviews → findings → approval → report), so a flat set of routes plus a single layout component is sufficient. No nested routing or layout abstraction is justified yet.

### 4. Session context as the only identity source
A single `SessionContext` owns `userId`, `projectId`, `role`, persisted to `localStorage` under a versioned key. The API client refuses to send a request without an active session. This mirrors the backend's `X-User-ID`/`X-Project-ID`/`X-Role` requirement.

### 5. Client-side role gating is presentation-only
The UI hides affordances the role cannot exercise, but the backend remains the authorization source of truth. This avoids duplicated authorization logic drifting from the backend.

### 6. Mirrored DTOs, not a generated client
`src/api/types.ts` mirrors backend Pydantic models field-for-field. Drift is detected in code review and in CI by typecheck. A future change can replace this with an OpenAPI-generated client once the backend stabilizes.

### 7. Vitest + jsdom + React Testing Library
Lightweight, integrates with Vite, and supports the components and client we have.

### 8. Frontend OpenSpec store mirrors the backend store
`frontend/openspec/` mirrors the layout used in `backend/openspec/` (config.yaml, changes/, specs/). The first capability introduced is `frontend-shell`. Future capabilities (e.g., per-page workflows) can be added incrementally without changing this convention.

## Risks / Trade-offs

- **DTO drift**: hand-maintained types can diverge from backend schemas. Mitigation: add a follow-up change to consume the backend's OpenAPI schema once `create_app()` ships a stable OpenAPI URL.
- **Session in `localStorage`**: not secure against XSS, but acceptable for this scope (no secrets stored, backend remains authoritative). A future change can move to HttpOnly cookies + CSRF tokens.
- **No server-side rendering**: SEO is not a goal. The report page renders the backend's plain-text Markdown report directly.
- **Strict typing cost**: every new endpoint requires updating `src/api/types.ts` and `src/api/client.ts`. Accepted for the type-safety payoff.
- **Accessibility scope**: we follow WCAG-friendly defaults (semantic HTML, labels, keyboard nav) but a full accessibility audit is out of scope for this change.
