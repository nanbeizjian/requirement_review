# Add frontend scaffold

## Why

The repository currently ships a FastAPI backend and root public-contract spec, but has no client surface. Reviewers, admins, and viewers need a web UI to create projects, upload knowledge, submit requirements, decide findings, approve reviews, and read reports. The backend is already a complete public HTTP API; the frontend must consume it without redefining any contract.

## What Changes

- Introduce a new `frontend/` component containing a TypeScript + React + Vite single-page application.
- Add a typed HTTP client (`src/api/client.ts`) that mirrors backend Pydantic field names and injects the `X-User-ID`, `X-Project-ID`, and `X-Role` headers from a session context on every request.
- Add session controls, routing, and pages for projects, knowledge upload, review creation, review detail, findings, approval, and report.
- Add a new component OpenSpec store under `frontend/openspec/` mirroring the existing backend OpenSpec store layout.
- Add a new component capability `frontend-shell` capturing UI, session, client, error-surfacing, and accessibility behavior.
- Add a `frontend/AGENTS.md` declaring inheritance from the root rules and frontend-specific engineering constraints.
- Update the root `.gitignore` to ignore frontend build artifacts.

No root public contract changes. The proposal references `openspec/specs/public-contracts/spec.md` for project isolation, human approval, evidence traceability, and compatible errors.

## Capabilities

### New Capabilities

- `frontend-shell`: The single-page app shell, session context, typed API client, error surface, accessibility, idempotency-key generation, and routing for the projects/knowledge/reviews/findings/approval/report workflows.

### Modified Capabilities

- None. The root public-contract spec and the backend component are not modified.

## Impact

- New files: `frontend/` directory, `frontend/openspec/` directory, `frontend/AGENTS.md`.
- Updated: root `.gitignore` (adds frontend ignores).
- Affected systems: developers running the UI, CI for lint/typecheck/test.
- Public API impact: none — frontend only consumes the existing public API.
- Dependencies added: `react`, `react-dom`, `react-router-dom` (runtime); `vite`, `@vitejs/plugin-react`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `eslint`, `@typescript-eslint/*`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `typescript`, `@types/react`, `@types/react-dom` (dev).

## Non-goals

- Authentication or single sign-on. Sessions are local-only and identify the caller via headers, not tokens.
- Mobile-native or Electron shells.
- Editing the root public-contract spec or backend OpenSpec store as part of this change.
- Production deployment pipeline (Docker, hosting) for the frontend — left for a follow-up change.
- Internationalization beyond the existing `lang="en"` baseline.
