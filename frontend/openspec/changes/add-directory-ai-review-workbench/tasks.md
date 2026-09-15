## 1. Frontend foundation and API boundary

- [ ] 1.1 Create the React, TypeScript strict, Vite, React Router, Vitest, Testing Library, and ESLint project files; verify dependency installation, typecheck, and a smoke render test succeed.
- [ ] 1.2 Define API types that mirror the approved root public contract and implement one session-aware client for listing/creating reviews, polling status, reading findings, deciding findings, approving documents, and reading reports; verify client tests assert identity headers, idempotency keys, response decoding, and safe error mapping.
- [ ] 1.3 Implement SessionContext and an accessible application shell with reviewer/viewer affordance gating; verify role-focused component tests pass.

## 2. Directory submission workflow

- [ ] 2.1 Add failing tests for Markdown filtering, directory metadata preview, ignored-file counts, multi-file fallback, absence of absolute paths in requests, and isolated file failures.
- [ ] 2.2 Implement directory/multi-file selection, UTF-8 reading, preview, bounded submission queue, per-file progress, and isolated retry; verify the directory workflow tests pass.
- [ ] 2.3 Implement capped polling with cancellation and terminal-state handling; verify fake-timer tests cover backoff, completion, failure, and unmount cancellation.

## 3. Review records and report

- [ ] 3.1 Add failing page tests for restored review lists, finding cards with required evidence fields, decision filters, pending counts, accessible status announcements, and viewer read-only behavior.
- [ ] 3.2 Implement project review list and review detail pages with semantic status summaries and one record per finding; verify page and keyboard-navigation tests pass.
- [ ] 3.3 Add failing interaction tests for accept/reject/re-review, retry-stable idempotency keys, duplicate-submit prevention, and decision refresh; implement decision forms and verify tests pass for reviewer/admin while viewer remains read-only.
- [ ] 3.4 Add failing tests for the final-confirmation gate, zero-finding confirmation, successful approval, and report rendering; implement final confirmation and report page, then verify those tests pass.

## 4. Frontend validation

- [ ] 4.1 Run `openspec validate add-directory-ai-review-workbench --strict` from `frontend/` and fix all component change validation errors.
- [ ] 4.2 Run `npm run lint`, `npm run typecheck`, `npm test -- --run`, and `npm run build` from `frontend/`; fix regressions and record successful outputs.
- [ ] 4.3 Run a browser-level integration flow with multiple Markdown files that verifies independent submission, multiple finding records per document, per-finding decisions, refresh recovery, final approval gating, accessible controls, and report availability.
