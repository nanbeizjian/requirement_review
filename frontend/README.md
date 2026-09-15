# Requirement Review Frontend

Web UI for the [requirement review backend](../backend). Consumes the public HTTP API defined in `openspec/specs/public-contracts/spec.md` and does not redefine any contract.

## Stack

- React 18 + TypeScript (`strict`)
- Vite for dev server and production bundling
- React Router for client routing
- Vitest + jsdom + React Testing Library for tests

## Layout

```
frontend/
├── AGENTS.md           # Component-specific agent rules (inherits root)
├── openspec/           # Component OpenSpec store
│   ├── config.yaml
│   ├── changes/
│   └── specs/
├── src/
│   ├── api/            # Typed HTTP client + DTO mirrors of backend Pydantic models
│   ├── components/     # AppShell, ErrorBanner
│   ├── lib/            # Error mapping, hooks
│   ├── routes/         # One file per page
│   ├── session/        # SessionContext (X-User-ID / X-Project-ID / X-Role)
│   ├── styles.css
│   ├── App.tsx
│   └── main.tsx
└── package.json
```

## Local development

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173 (proxies /api → http://localhost:8000)
npm run typecheck
npm run lint
npm test -- --run
```

## Authorization and sessions

- The header `X-User-ID`, `X-Project-ID`, `X-Role` must match the active session for every request. Use the session controls in the header bar.
- The UI hides affordances the active role cannot exercise. The backend remains the source of truth — never rely on the client to enforce authorization.

## Errors

All non-2xx responses are decoded into the stable `ApiError` shape (`code`, `message`, `correlation_id`) defined in `openspec/specs/public-contracts/spec.md`. Stack traces and secrets are never exposed.

## Idempotency

Approval and finding-decision requests generate a per-action idempotency key in the UI. The key is surfaced for retry safety.
