## 1. Bootstrap frontend directory and tooling

- [x] 1.1 Create `frontend/AGENTS.md` declaring inheritance from root and frontend engineering rules
- [x] 1.2 Create `frontend/package.json`, `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `index.html`, `.eslintrc.cjs`
- [x] 1.3 Create `frontend/.gitignore` and update root `.gitignore` to ignore `frontend/node_modules/`, `frontend/dist/`, etc.
- [x] 1.4 Add `frontend/README.md` describing stack, layout, and local development
- [x] 1.5 Run `npm install` in `frontend/` to verify dependencies resolve (deferred until CI installs them)

## 2. Implement session context and typed API client

- [x] 2.1 Add `src/session/SessionContext.tsx` with `SessionProvider`, `useSession`, localStorage persistence
- [x] 2.2 Add `src/api/types.ts` mirroring backend Pydantic models (DataPolicy, ReviewStatus, ReviewFinding, etc.)
- [x] 2.3 Add `src/lib/errors.ts` implementing `ApiError` and `readError` over the stable error contract
- [x] 2.4 Add `src/api/client.ts` with `RequirementReviewClient` covering projects, knowledge, reviews, findings, approval, report
- [x] 2.5 Add `src/lib/useClient.ts` hook returning the singleton client
- [x] 2.6 Add `newIdempotencyKey(prefix)` helper and require `Idempotency-Key` on approval/decision calls

## 3. Implement routing and pages

- [x] 3.1 Add `src/components/AppShell.tsx` and `src/components/ErrorBanner.tsx`
- [x] 3.2 Add `src/styles.css` with the layout primitives
- [x] 3.3 Add `src/App.tsx` with route table and `src/main.tsx` bootstrapping `SessionProvider` + `BrowserRouter`
- [x] 3.4 Add `src/routes/ProjectsPage.tsx` (admin-only project create)
- [x] 3.5 Add `src/routes/KnowledgeUploadPage.tsx` (admin-only upload, projectId-mismatch guard)
- [x] 3.6 Add `src/routes/ReviewCreatePage.tsx` (reviewer/admin review submission)
- [x] 3.7 Add `src/routes/ReviewListPage.tsx` and `src/routes/ReviewDetailPage.tsx`
- [x] 3.8 Add `src/routes/FindingsPage.tsx` with accept/reject/re-review actions and per-action idempotency keys
- [x] 3.9 Add `src/routes/ApprovalPage.tsx` with approve/modify/reject/re-review and idempotency-key surfacing
- [x] 3.10 Add `src/routes/ReportPage.tsx` rendering the backend Markdown report
- [x] 3.11 Add `src/routes/NotFoundPage.tsx`

## 4. Add tests

- [x] 4.1 Add `src/__tests__/setup.ts` wiring `@testing-library/jest-dom`
- [x] 4.2 Add `src/__tests__/client.test.ts` covering header injection, idempotency keys, error decoding, and Markdown validation
- [x] 4.3 Run `npm run lint`, `npm run typecheck`, and `npm test -- --run` from `frontend/` (deferred until `npm install` runs in CI)

## 5. OpenSpec documentation

- [x] 5.1 Create `frontend/openspec/config.yaml` declaring stack, context, and rules
- [x] 5.2 Add `frontend/openspec/changes/.gitkeep`, `archive/.gitkeep`, `specs/.gitkeep`
- [x] 5.3 Create the `add-frontend-scaffold` change with `proposal.md`, `design.md`, `tasks.md`, and `specs/frontend-shell/spec.md`
- [x] 5.4 Run `openspec validate` from `frontend/` and from the repository root

## 6. Validation

- [x] 6.1 Run `openspec validate` at the repository root (no root-level changes; expect a clean baseline)
- [x] 6.2 Run `openspec validate` inside `frontend/` and confirm the `add-frontend-scaffold` change is well-formed
- [x] 6.3 Confirm the frontend change does NOT modify `openspec/specs/public-contracts/spec.md`
