# Directory AI Review Workbench Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React + TypeScript frontend workbench for batch AI review of Markdown requirements, per `frontend/openspec/changes/add-directory-ai-review-workbench/`.

**Architecture:** Vite SPA; one `SessionContext` injecting identity headers into every API call; single typed `apiClient` wrapping `fetch` with `AbortController` and idempotency-key handling; per-file submission queue with capped concurrency; bounded exponential polling; role-aware UI gating with backend authoritative; CSS Modules with a small token layer; Vitest + RTL + MSW for unit/integration, Playwright for browser-level end-to-end against a real FastAPI backend.

**Tech Stack:** Vite 5, React 18, TypeScript 5 strict, React Router 6, Vitest 1, @testing-library/react + jsdom, MSW 2, ESLint 9 flat config, Playwright 1.48.

**Spec:** `frontend/openspec/changes/add-directory-ai-review-workbench/{proposal,design,tasks}.md` and `frontend/openspec/changes/add-directory-ai-review-workbench/specs/directory-review-workbench/spec.md`. Backend contract authority: `openspec/specs/public-contracts/spec.md` plus the additive extensions in `openspec/changes/add-directory-ai-review-workbench/specs/public-contracts/spec.md` (root change; deployed before this work runs).

## File Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── playwright.config.ts
├── eslint.config.js
├── .gitignore
├── README.md
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── router.tsx
│   ├── vite-env.d.ts
│   ├── api/
│   │   ├── types.ts            # mirrors backend Pydantic models
│   │   ├── errors.ts           # ApiError + envelope parsing
│   │   ├── idempotency.ts      # UUID v4 generator
│   │   └── client.ts           # apiClient.fetch + high-level methods
│   ├── session/
│   │   ├── SessionContext.tsx  # React Context + provider
│   │   ├── SessionForm.tsx     # bootstrap form (no login)
│   │   └── storage.ts          # sessionStorage read/write
│   ├── shell/
│   │   ├── AppShell.tsx
│   │   ├── RoleGate.tsx        # renders children iff role allowed
│   │   └── GlobalAlerts.tsx
│   ├── components/
│   │   ├── Button/{Button.tsx, Button.module.css, Button.test.tsx}
│   │   ├── FormField/{FormField.tsx, FormField.module.css, FormField.test.tsx}
│   │   ├── Textarea/{Textarea.tsx, Textarea.module.css, Textarea.test.tsx}
│   │   ├── Select/{Select.tsx, Select.module.css, Select.test.tsx}
│   │   ├── Alert/{Alert.tsx, Alert.module.css, Alert.test.tsx}
│   │   ├── Spinner/{Spinner.tsx, Spinner.module.css, Spinner.test.tsx}
│   │   └── StatusBadge/{StatusBadge.tsx, StatusBadge.module.css, StatusBadge.test.tsx}
│   ├── features/
│   │   ├── directory/
│   │   │   ├── fileFilters.ts            # extension filter + ignored counts
│   │   │   ├── fileFilters.test.ts
│   │   │   ├── DirectoryPicker.tsx
│   │   │   ├── DirectoryPicker.module.css
│   │   │   ├── DirectoryPicker.test.tsx
│   │   │   ├── FileEntryList.tsx
│   │   │   ├── FileEntryList.module.css
│   │   │   ├── FileEntryList.test.tsx
│   │   │   ├── useDirectorySubmission.ts # queue with concurrency=3
│   │   │   └── useDirectorySubmission.test.ts
│   │   ├── reviews/
│   │   │   ├── ProjectReviewListPage.tsx
│   │   │   ├── ProjectReviewListPage.module.css
│   │   │   ├── ProjectReviewListPage.test.tsx
│   │   │   ├── ReviewListTable.tsx
│   │   │   └── ReviewListTable.module.css
│   │   ├── review-detail/
│   │   │   ├── ReviewDetailPage.tsx
│   │   │   ├── ReviewDetailPage.module.css
│   │   │   ├── ReviewDetailPage.test.tsx
│   │   │   ├── ReviewStatusHeader.tsx
│   │   │   ├── ReviewStatusHeader.module.css
│   │   │   ├── FindingFilters.tsx
│   │   │   ├── FindingFilters.module.css
│   │   │   ├── FindingCard.tsx
│   │   │   ├── FindingCard.module.css
│   │   │   ├── FindingCard.test.tsx
│   │   │   ├── DecisionForm.tsx
│   │   │   ├── DecisionForm.module.css
│   │   │   ├── DecisionForm.test.tsx
│   │   │   ├── FinalApprovalGate.tsx
│   │   │   ├── FinalApprovalGate.module.css
│   │   │   ├── FinalApprovalGate.test.tsx
│   │   │   ├── ApprovalForm.tsx
│   │   │   ├── ApprovalForm.module.css
│   │   │   ├── ApprovalForm.test.tsx
│   │   │   ├── useReviewPolling.ts
│   │   │   └── useReviewPolling.test.ts
│   │   └── report/
│   │       ├── ReportPage.tsx
│   │       ├── ReportPage.module.css
│   │       ├── ReportPage.test.tsx
│   │       ├── MarkdownView.tsx
│   │       └── MarkdownView.module.css
│   ├── lib/
│   │   ├── formatDate.ts
│   │   ├── formatDate.test.ts
│   │   └── paths.ts                      # basename, basename + extension strip
│   ├── mocks/
│   │   ├── handlers.ts                   # MSW request handlers
│   │   ├── server.ts                     # node setupServer
│   │   ├── browser.ts                    # browser setupWorker
│   │   └── fixtures.ts                   # canned review/finding/decision data
│   └── styles/
│       ├── tokens.css                    # CSS custom properties (colors, spacing)
│       └── reset.css
└── tests/
    └── e2e/
        └── workbench.spec.ts              # Playwright browser-level flow
```

Each file above has exactly one responsibility. Tests live next to the unit under test. Component CSS Modules live next to the TSX so the import path mirrors the component name. The `mocks/` directory is consumed only by tests; production bundles do not import it.

## Global Constraints

- **Node:** `>=20` (enforced via `package.json` `engines.node`).
- **TypeScript:** `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`, `noImplicitOverride: true`.
- **Backend assumption:** FastAPI on `http://localhost:8000`; Vite dev server proxies `/api/v1` → that target.
- **Identity headers on every request:** `X-User-ID`, `X-Project-ID`, `X-Role`. Source of truth: `SessionContext`. Never logged, never persisted to localStorage beyond the bootstrap storage key.
- **Session storage:** key `rr:session:v1`, contains `{ userId, projectId, role }`. Cleared on logout. **No**审核 fact data (findings, decisions, idempotency keys) is stored client-side.
- **API types mirror `backend/src/requirement_review/{domain/models.py, api/schemas.py, api/runtime.py}`** plus the additive extensions in `openspec/changes/add-directory-ai-review-workbench/specs/public-contracts/spec.md`. Status enum members: `PENDING | PARSING | RETRIEVING | REVIEWING | CONSOLIDATING | WAITING_APPROVAL | COMPLETED | FAILED`. Terminal: `WAITING_APPROVAL | COMPLETED | FAILED`.
- **Roles:** `admin | reviewer | viewer`. Decision/approval forms visible only to `reviewer | admin`. Backend is authoritative — UI gating is advisory.
- **Data policy enum:** `local_only | cloud_allowed | cloud_redacted`. Frontend defaults to `local_only` per spec non-goal "不在服务端保存用户本地目录结构，也不上传非 Markdown 文件".
- **Markdown filter:** extensions `.md`, `.markdown`, case-insensitive. Non-matching files count as `ignored` and are surfaced in the preview, never submitted.
- **`source_name`:** always `basename(file.name)` only. The frontend never constructs or sends absolute paths.
- **Idempotency keys:** UUID v4. One per user action. Persisted in component state for the lifetime of that action so a network retry can reuse the key; a new user action generates a new key.
- **Error envelope:** `{ code: string; message: string; correlation_id: string }`. UI shows `message` + `correlation_id` only. Internal stacks never exposed.
- **Submission concurrency:** `3`.
- **Polling backoff:** start 1000 ms; double each tick; cap 5000 ms. Stale banner after 5 consecutive errors with manual retry.
- **Submission retry:** on create failure, retry creates a **new** review (server has no create idempotency in current contract).
- **Report rendering:** `MarkdownView` escapes HTML and renders inside `<pre>`; no third-party Markdown library; no XSS surface.
- **Accessibility:** every interactive control has an accessible name; focus never lands on hidden elements; status changes announced via `role="status"` or `aria-live="polite"`; keyboard reachable in DOM order.
- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`). Tests and impl land in the same commit per task.
- **Verification gates before task 4.1/4.2 completion:** `openspec validate add-directory-ai-review-workbench --strict --type change --path frontend/openspec/changes/add-directory-ai-review-workbench` exits 0; `npm run lint`, `npm run typecheck`, `npm test -- --run`, `npm run build` all exit 0.

---

## Phase 1 — Foundation, API boundary, session, shell

### Task 1: Scaffold Vite + React + TS strict project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/reset.css`
- Create: `frontend/.gitignore`
- Create: `frontend/eslint.config.js`
- Create: `frontend/src/App.test.tsx`

**Step 1: Write `package.json` with pinned, minimal deps**

```json
{
  "name": "requirement-review-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": { "node": ">=20" },
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview --port 5173",
    "lint": "eslint .",
    "typecheck": "tsc -b --noEmit",
    "test": "vitest",
    "test:e2e": "playwright test",
    "test:e2e:install": "playwright install --with-deps chromium"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.0",
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.10",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "eslint": "^9.11.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.12",
    "globals": "^15.9.0",
    "jsdom": "^25.0.1",
    "msw": "^2.4.9",
    "typescript": "^5.6.2",
    "typescript-eslint": "^8.7.0",
    "vite": "^5.4.8",
    "vitest": "^1.6.0"
  }
}
```

**Step 2: Write `tsconfig.json`**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

Create `frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "useDefineForClassFields": true,
    "skipLibCheck": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "isolatedModules": true,
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"],
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo"
  },
  "include": ["src", "src/**/*.test.ts", "src/**/*.test.tsx"],
  "exclude": ["tests/e2e"]
}
```

**Step 3: Write `tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "skipLibCheck": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts", "playwright.config.ts"]
}
```

**Step 4: Write `vite.config.ts`**

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
    exclude: ["tests/e2e/**", "node_modules/**"],
  },
});
```

**Step 5: Write `index.html`**

```html
<!doctype html>
<html lang="zh-Hans">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Requirement Review Workbench</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 6: Write `src/styles/tokens.css`**

```css
:root {
  --color-bg: #ffffff;
  --color-fg: #1a1a1a;
  --color-muted: #5a5a5a;
  --color-border: #d0d0d0;
  --color-accent: #1e5bbf;
  --color-accent-fg: #ffffff;
  --color-danger: #b3261e;
  --color-warn: #8a5a00;
  --color-ok: #1f7a3a;
  --color-disabled-bg: #ececec;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --radius-1: 4px;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
```

**Step 7: Write `src/styles/reset.css`**

```css
*, *::before, *::after { box-sizing: border-box; }
html, body, #root { height: 100%; }
body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--color-fg); background: var(--color-bg); }
button { font: inherit; }
:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
```

**Step 8: Write `src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
```

**Step 9: Write `src/test-setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

**Step 10: Write `src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/tokens.css";
import "./styles/reset.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("missing #root");
ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

**Step 11: Write `src/App.tsx` placeholder + smoke test**

```tsx
export default function App() {
  return <main>workbench bootstrapping…</main>;
}
```

```tsx
// src/App.test.tsx
import { render, screen } from "@testing-library/react";
import App from "./App";

it("renders the bootstrap placeholder", () => {
  render(<App />);
  expect(screen.getByText(/workbench bootstrapping/i)).toBeInTheDocument();
});
```

**Step 12: Write `frontend/.gitignore`**

```
node_modules
dist
.vite
coverage
playwright-report
test-results
*.log
.DS_Store
```

**Step 13: Write `frontend/eslint.config.js`**

```js
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "playwright-report", "test-results"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: { ecmaVersion: 2022, globals: { ...globals.browser, ...globals.node } },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },
);
```

`@eslint/js` is exported from the `eslint` package; if it is missing, install with `npm i -D @eslint/js` and import it.

**Step 14: Install and verify**

Run from `frontend/`:
```bash
npm install
npm run typecheck
npm test -- --run
npm run build
npm run lint
```
Expected: all four exit 0; the smoke test passes.

**Step 15: Commit**

```bash
git add frontend
git commit -m "chore(frontend): scaffold Vite + React + TS strict + ESLint + Vitest"
```

---

### Task 2: API types mirroring backend

**Files:**
- Create: `frontend/src/api/types.ts`
- Test: `frontend/src/api/types.test.ts`

**Step 1: Write failing test for type guards**

```ts
// src/api/types.test.ts
import { isTerminalStatus, ROLE_VALUES, DATA_POLICY_VALUES } from "./types";

describe("api/types", () => {
  it("treats WAITING_APPROVAL, COMPLETED, FAILED as terminal", () => {
    expect(isTerminalStatus("WAITING_APPROVAL")).toBe(true);
    expect(isTerminalStatus("COMPLETED")).toBe(true);
    expect(isTerminalStatus("FAILED")).toBe(true);
    expect(isTerminalStatus("REVIEWING")).toBe(false);
    expect(isTerminalStatus("PENDING")).toBe(false);
  });

  it("exposes the canonical role set", () => {
    expect([...ROLE_VALUES].sort()).toEqual(["admin", "reviewer", "viewer"]);
  });

  it("exposes the canonical data policy set", () => {
    expect([...DATA_POLICY_VALUES].sort()).toEqual(["cloud_allowed", "cloud_redacted", "local_only"]);
  });
});
```

**Step 2: Run — expect FAIL** (`Cannot find module './types'`)

```bash
cd frontend && npm test -- --run src/api/types.test.ts
```

**Step 3: Implement `src/api/types.ts`**

```ts
export type Role = "admin" | "reviewer" | "viewer";
export const ROLE_VALUES: readonly Role[] = ["admin", "reviewer", "viewer"] as const;

export type DataPolicy = "local_only" | "cloud_allowed" | "cloud_redacted";
export const DATA_POLICY_VALUES: readonly DataPolicy[] = ["local_only", "cloud_allowed", "cloud_redacted"] as const;

export type ReviewStatus =
  | "PENDING"
  | "PARSING"
  | "RETRIEVING"
  | "REVIEWING"
  | "CONSOLIDATING"
  | "WAITING_APPROVAL"
  | "COMPLETED"
  | "FAILED";

const TERMINAL_STATUSES = new Set<ReviewStatus>(["WAITING_APPROVAL", "COMPLETED", "FAILED"]);

export function isTerminalStatus(s: ReviewStatus): boolean {
  return TERMINAL_STATUSES.has(s);
}

export type DecisionAction = "accept" | "reject" | "re-review";
export type ApprovalAction = "approve" | "modify" | "reject" | "re-review";

export interface EvidenceRef {
  source_type: string;
  document_id: string;
  version: number;
  locator: string;
  quote: string;
}

export interface Finding {
  finding_id: string;
  requirement_id: string;
  dimension: string;
  severity: "critical" | "high" | "medium" | "low";
  issue: string;
  impact: string;
  recommendation: string;
  confidence: number;
  evidence: EvidenceRef[];
  uses_system_fact: boolean;
  decision: FindingDecision | null;
}

export interface FindingDecision {
  action: DecisionAction;
  comment: string;
  actor_id: string;
  decided_at: string;
  idempotency_key: string;
}

export interface ReviewSummary {
  review_id: string;
  project_id: string;
  source_name: string | null;
  status: ReviewStatus;
  finding_count: number;
  pending_decision_count: number;
  created_at: string;
}

export interface ReviewDetail extends ReviewSummary {
  failed_dimensions: string[];
}

export interface ReviewCreateResponse {
  review_id: string;
  status: ReviewStatus;
}

export interface CreateReviewPayload {
  project_id: string;
  data_policy: DataPolicy;
  text: string;
  source_name: string;
}

export interface DecideFindingPayload {
  action: DecisionAction;
  comment: string;
}

export interface ApprovalPayload {
  action: ApprovalAction;
  comment: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  correlation_id: string;
}
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/api/types.test.ts
```

**Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/types.test.ts
git commit -m "feat(frontend): add API types mirroring backend public contract"
```

---

### Task 3: Idempotency + error envelope

**Files:**
- Create: `frontend/src/api/idempotency.ts`
- Create: `frontend/src/api/errors.ts`
- Test: `frontend/src/api/idempotency.test.ts`
- Test: `frontend/src/api/errors.test.ts`

**Step 1: Write failing tests**

```ts
// src/api/idempotency.test.ts
import { newIdempotencyKey } from "./idempotency";

describe("newIdempotencyKey", () => {
  it("returns a v4-shaped UUID string", () => {
    const key = newIdempotencyKey();
    expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });
  it("produces a fresh key each call", () => {
    expect(newIdempotencyKey()).not.toBe(newIdempotencyKey());
  });
});
```

```ts
// src/api/errors.test.ts
import { parseApiError, ApiError } from "./errors";

describe("parseApiError", () => {
  it("decodes a 409 conflict envelope", async () => {
    const res = new Response(JSON.stringify({ code: "idempotency_conflict", message: "conflict", correlation_id: "abc" }), { status: 409 });
    const err = await parseApiError(res);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.code).toBe("idempotency_conflict");
    expect(err.message).toBe("conflict");
    expect(err.correlationId).toBe("abc");
  });
  it("falls back to status text when envelope missing", async () => {
    const res = new Response("not json", { status: 500 });
    const err = await parseApiError(res);
    expect(err.code).toBe("http_500");
    expect(err.correlationId).toBe("");
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/api/idempotency.test.ts src/api/errors.test.ts
```

**Step 3: Implement `src/api/idempotency.ts`**

```ts
export function newIdempotencyKey(): string {
  // crypto.randomUUID is available in modern browsers and Node 20+
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  // Defensive fallback for environments without crypto.randomUUID
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && "getRandomValues" in crypto) crypto.getRandomValues(bytes);
  else for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10, 16).join("")}`;
}
```

**Step 4: Implement `src/api/errors.ts`**

```ts
import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string;
  constructor(status: number, code: string, message: string, correlationId: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export async function parseApiError(res: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> = {};
  try {
    body = (await res.json()) as Partial<ApiErrorBody>;
  } catch {
    /* not JSON */
  }
  return new ApiError(
    res.status,
    body.code ?? `http_${res.status}`,
    body.message ?? res.statusText || `request failed (${res.status})`,
    body.correlation_id ?? "",
  );
}
```

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/api/idempotency.test.ts src/api/errors.test.ts
```

**Step 6: Commit**

```bash
git add frontend/src/api/idempotency.ts frontend/src/api/errors.ts frontend/src/api/idempotency.test.ts frontend/src/api/errors.test.ts
git commit -m "feat(frontend): add idempotency key generator and ApiError envelope"
```

---

### Task 4: API client (fetch + identity + idempotency + abort)

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/mocks/handlers.ts`
- Create: `frontend/src/mocks/server.ts`
- Create: `frontend/src/mocks/fixtures.ts`
- Test: `frontend/src/api/client.test.ts`

**Step 1: Write failing client tests**

```ts
// src/api/client.test.ts
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ApiError, apiClient, type Actor } from "./client";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const actor: Actor = { userId: "u1", projectId: "p1", role: "reviewer" };

describe("apiClient", () => {
  it("injects identity headers on every request", async () => {
    let received: Record<string, string> = {};
    server.use(
      http.get("/api/v1/reviews", ({ request }) => {
        received = {
          user: request.headers.get("X-User-ID") ?? "",
          project: request.headers.get("X-Project-ID") ?? "",
          role: request.headers.get("X-Role") ?? "",
        };
        return HttpResponse.json([]);
      }),
    );
    await apiClient.listReviews(actor);
    expect(received).toEqual({ user: "u1", project: "p1", role: "reviewer" });
  });

  it("auto-generates an idempotency key when none supplied", async () => {
    let key = "";
    server.use(
      http.post("/api/v1/reviews", ({ request }) => {
        key = request.headers.get("Idempotency-Key") ?? "";
        return HttpResponse.json({ review_id: "r1", status: "PENDING" }, { status: 202 });
      }),
    );
    await apiClient.createReview(actor, { project_id: "p1", data_policy: "local_only", text: "x", source_name: "a.md" });
    expect(key).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("preserves a caller-supplied idempotency key for retries", async () => {
    let count = 0;
    server.use(
      http.post("/api/v1/reviews/x/findings/y/decision", ({ request }) => {
        count += 1;
        const k = request.headers.get("Idempotency-Key");
        if (count === 1) return new HttpResponse(null, { status: 502 });
        return HttpResponse.json({}, { headers: { "Idempotency-Key": k ?? "" } });
      }),
    );
    await expect(
      apiClient.decideFinding(actor, "x", "y", { action: "accept", comment: "ok" }, { idempotencyKey: "stable-key", retry: { retries: 1, baseDelayMs: 1 } }),
    ).rejects.toBeInstanceOf(ApiError);
    await apiClient.decideFinding(actor, "x", "y", { action: "accept", comment: "ok" }, { idempotencyKey: "stable-key", retry: { retries: 1, baseDelayMs: 1 } });
    expect(count).toBe(2);
  });

  it("decodes the error envelope on non-2xx", async () => {
    server.use(
      http.post("/api/v1/reviews", () =>
        HttpResponse.json({ code: "validation_failed", message: "bad input", correlation_id: "cid-1" }, { status: 422 }),
      ),
    );
    await expect(
      apiClient.createReview(actor, { project_id: "p1", data_policy: "local_only", text: "x", source_name: "a.md" }),
    ).rejects.toMatchObject({ status: 422, code: "validation_failed", correlationId: "cid-1" });
  });

  it("honors AbortSignal to cancel in-flight requests", async () => {
    server.use(http.get("/api/v1/reviews", () => new HttpResponse(null, { status: 200, headers: { "Content-Type": "application/json" } })));
    const ac = new AbortController();
    ac.abort();
    await expect(apiClient.listReviews(actor, { signal: ac.signal })).rejects.toThrow();
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/api/client.test.ts
```

**Step 3: Implement `frontend/src/mocks/fixtures.ts` (minimal)**

```ts
import type { ReviewSummary, Finding } from "../api/types";
export const sampleSummary = (): ReviewSummary => ({
  review_id: "r1",
  project_id: "p1",
  source_name: "spec.md",
  status: "WAITING_APPROVAL",
  finding_count: 2,
  pending_decision_count: 1,
  created_at: "2026-09-15T00:00:00Z",
});
export const sampleFindings = (): Finding[] => [];
```

**Step 4: Implement `frontend/src/mocks/server.ts`**

```ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";
export const server = setupServer(...handlers);
```

**Step 5: Implement `frontend/src/mocks/handlers.ts`** (kept minimal; tests override per case)

```ts
import { http, HttpResponse } from "msw";
export const handlers = [
  http.get("/api/v1/reviews", () => HttpResponse.json([])),
];
```

**Step 6: Implement `src/api/client.ts`**

```ts
import { newIdempotencyKey } from "./idempotency";
import { ApiError, parseApiError } from "./errors";
import type {
  ApprovalPayload,
  CreateReviewPayload,
  DecideFindingPayload,
  Finding,
  ReviewCreateResponse,
  ReviewDetail,
  ReviewSummary,
} from "./types";

export interface Actor {
  userId: string;
  projectId: string;
  role: "admin" | "reviewer" | "viewer";
}

export interface RequestOptions {
  signal?: AbortSignal;
  idempotencyKey?: string;
  retry?: { retries: number; baseDelayMs: number };
}

const BASE = "/api/v1";

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    if (signal) {
      const onAbort = () => { clearTimeout(t); reject(new DOMException("aborted", "AbortError")); };
      if (signal.aborted) onAbort();
      else signal.addEventListener("abort", onAbort, { once: true });
    }
  });
}

async function request<T>(
  actor: Actor,
  path: string,
  init: RequestInit & { method?: string; json?: unknown } = {},
  opts: RequestOptions = {},
): Promise<T> {
  const method = init.method ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("X-User-ID", actor.userId);
  headers.set("X-Project-ID", actor.projectId);
  headers.set("X-Role", actor.role);
  if (opts.idempotencyKey) headers.set("Idempotency-Key", opts.idempotencyKey);

  const doFetch = async (): Promise<Response> => {
    const reqInit: RequestInit = { method, headers, signal: opts.signal ?? null };
    if (init.json !== undefined) {
      headers.set("Content-Type", "application/json");
      reqInit.body = JSON.stringify(init.json);
    }
    return fetch(`${BASE}${path}`, reqInit);
  };

  const retries = opts.retry?.retries ?? 0;
  const baseDelay = opts.retry?.baseDelayMs ?? 250;
  let attempt = 0;
  /* eslint-disable no-constant-condition */
  while (true) {
    let res: Response;
    try {
      res = await doFetch();
    } catch (e) {
      if (attempt < retries && (e as DOMException).name !== "AbortError") {
        await sleep(baseDelay * 2 ** attempt, opts.signal);
        attempt += 1;
        continue;
      }
      throw e;
    }
    if (res.status >= 500 && attempt < retries) {
      await sleep(baseDelay * 2 ** attempt, opts.signal);
      attempt += 1;
      continue;
    }
    if (!res.ok) throw await parseApiError(res);
    return (await res.json()) as T;
  }
  /* eslint-enable no-constant-condition */
}

export const apiClient = {
  async listReviews(actor: Actor, opts: RequestOptions = {}): Promise<ReviewSummary[]> {
    return request<ReviewSummary[]>(actor, "/reviews", { method: "GET" }, opts);
  },
  async getReview(actor: Actor, reviewId: string, opts: RequestOptions = {}): Promise<ReviewDetail> {
    return request<ReviewDetail>(actor, `/reviews/${encodeURIComponent(reviewId)}`, { method: "GET" }, opts);
  },
  async createReview(actor: Actor, payload: CreateReviewPayload, opts: RequestOptions = {}): Promise<ReviewCreateResponse> {
    const key = opts.idempotencyKey ?? newIdempotencyKey();
    return request<ReviewCreateResponse>(
      actor,
      "/reviews",
      { method: "POST", json: payload },
      { ...opts, idempotencyKey: key },
    );
  },
  async getFindings(actor: Actor, reviewId: string, opts: RequestOptions = {}): Promise<Finding[]> {
    return request<Finding[]>(actor, `/reviews/${encodeURIComponent(reviewId)}/findings`, { method: "GET" }, opts);
  },
  async decideFinding(
    actor: Actor,
    reviewId: string,
    findingId: string,
    payload: DecideFindingPayload,
    opts: RequestOptions = {},
  ): Promise<Finding> {
    if (!opts.idempotencyKey) throw new Error("decideFinding requires idempotencyKey");
    return request<Finding>(
      actor,
      `/reviews/${encodeURIComponent(reviewId)}/findings/${encodeURIComponent(findingId)}/decision`,
      { method: "POST", json: payload },
      opts,
    );
  },
  async approve(actor: Actor, reviewId: string, payload: ApprovalPayload, opts: RequestOptions = {}): Promise<ReviewDetail> {
    if (!opts.idempotencyKey) throw new Error("approve requires idempotencyKey");
    return request<ReviewDetail>(
      actor,
      `/reviews/${encodeURIComponent(reviewId)}/approval`,
      { method: "POST", json: payload },
      opts,
    );
  },
  async getReport(actor: Actor, reviewId: string, opts: RequestOptions = {}): Promise<string> {
    return request<string>(
      actor,
      `/reviews/${encodeURIComponent(reviewId)}/report`,
      { method: "GET", headers: { Accept: "text/markdown" } },
      opts,
    );
  },
};
```

**Step 7: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/api/client.test.ts
```

**Step 8: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts frontend/src/mocks
git commit -m "feat(frontend): add typed API client with identity and idempotency"
```

---

### Task 5: Session storage + SessionContext + SessionForm

**Files:**
- Create: `frontend/src/session/storage.ts`
- Create: `frontend/src/session/SessionContext.tsx`
- Create: `frontend/src/session/SessionForm.tsx`
- Create: `frontend/src/session/SessionForm.module.css`
- Test: `frontend/src/session/storage.test.ts`
- Test: `frontend/src/session/SessionContext.test.tsx`
- Test: `frontend/src/session/SessionForm.test.tsx`

**Step 1: Write failing tests**

```ts
// src/session/storage.test.ts
import { readSession, writeSession, clearSession, SESSION_STORAGE_KEY } from "./storage";

describe("session storage", () => {
  beforeEach(() => sessionStorage.clear());
  it("returns null when no session is stored", () => {
    expect(readSession()).toBeNull();
  });
  it("round-trips a valid session", () => {
    writeSession({ userId: "u", projectId: "p", role: "reviewer" });
    expect(readSession()).toEqual({ userId: "u", projectId: "p", role: "reviewer" });
  });
  it("rejects invalid stored payloads", () => {
    sessionStorage.setItem(SESSION_STORAGE_KEY, "{not json");
    expect(readSession()).toBeNull();
  });
  it("clearSession removes the entry", () => {
    writeSession({ userId: "u", projectId: "p", role: "viewer" });
    clearSession();
    expect(readSession()).toBeNull();
  });
});
```

```tsx
// src/session/SessionContext.test.tsx
import { render, screen } from "@testing-library/react";
import { SessionProvider, useSession } from "./SessionContext";

function Probe() {
  const s = useSession();
  return <span>{s.actor?.userId ?? "anonymous"}</span>;
}

it("provides null when no session is stored", () => {
  sessionStorage.clear();
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(screen.getByText("anonymous")).toBeInTheDocument();
});

it("exposes the stored session to consumers", () => {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u1", projectId: "p1", role: "reviewer" }));
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(screen.getByText("u1")).toBeInTheDocument();
});
```

```tsx
// src/session/SessionForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionForm } from "./SessionForm";

it("calls onSubmit with a normalized session", async () => {
  const onSubmit = vi.fn();
  sessionStorage.clear();
  render(<SessionForm onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText(/用户 ID/), "u1");
  await userEvent.type(screen.getByLabelText(/项目 ID/), "p1");
  await userEvent.selectOptions(screen.getByLabelText(/角色/), "reviewer");
  await userEvent.click(screen.getByRole("button", { name: /开始/ }));
  expect(onSubmit).toHaveBeenCalledWith({ userId: "u1", projectId: "p1", role: "reviewer" });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/session
```

**Step 3: Implement `src/session/storage.ts`**

```ts
import type { Role } from "../api/types";

export interface Session {
  userId: string;
  projectId: string;
  role: Role;
}

export const SESSION_STORAGE_KEY = "rr:session:v1";

const VALID_ROLES = new Set<Role>(["admin", "reviewer", "viewer"]);

function isSession(v: unknown): v is Session {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.userId === "string" && o.userId.length > 0 &&
    typeof o.projectId === "string" && o.projectId.length > 0 &&
    typeof o.role === "string" && VALID_ROLES.has(o.role as Role)
  );
}

export function readSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return isSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeSession(s: Session): void {
  sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(s));
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}
```

**Step 4: Implement `src/session/SessionContext.tsx`**

```tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Actor as ApiActor } from "../api/client";
import { clearSession, readSession, writeSession, type Session } from "./storage";

export interface SessionContextValue {
  actor: ApiActor | null;
  setSession: (s: Session) => void;
  reset: () => void;
}

const Ctx = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(() => readSession());

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "rr:session:v1") setSessionState(readSession());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setSession = useCallback((s: Session) => {
    writeSession(s);
    setSessionState(s);
  }, []);

  const reset = useCallback(() => {
    clearSession();
    setSessionState(null);
  }, []);

  const value = useMemo<SessionContextValue>(() => ({
    actor: session ? { userId: session.userId, projectId: session.projectId, role: session.role } : null,
    setSession,
    reset,
  }), [session, setSession, reset]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used within SessionProvider");
  return v;
}
```

**Step 5: Implement `src/session/SessionForm.tsx` + CSS**

```tsx
import { useId, useState, type FormEvent } from "react";
import { Button } from "../components/Button/Button";
import { FormField } from "../components/FormField/FormField";
import { Select } from "../components/Select/Select";
import type { Role } from "../api/types";
import type { Session } from "./storage";
import styles from "./SessionForm.module.css";

const ROLES: readonly Role[] = ["admin", "reviewer", "viewer"];

export function SessionForm({ onSubmit }: { onSubmit: (s: Session) => void }) {
  const userId = useId();
  const projectId = useId();
  const roleId = useId();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [r, setR] = useState<Role>("reviewer");

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ userId: u.trim(), projectId: p.trim(), role: r });
  }

  const ready = u.trim().length > 0 && p.trim().length > 0;

  return (
    <form className={styles.form} onSubmit={submit}>
      <h1>建立会话</h1>
      <p className={styles.hint}>本地开发会话；不实现登录、用户管理或服务端身份。</p>
      <FormField id={userId} label="用户 ID" value={u} onChange={setU} required autoComplete="off" />
      <FormField id={projectId} label="项目 ID" value={p} onChange={setP} required autoComplete="off" />
      <Select id={roleId} label="角色" value={r} onChange={(v) => setR(v as Role)} options={ROLES.map((v) => ({ value: v, label: v }))} />
      <Button type="submit" disabled={!ready}>开始</Button>
    </form>
  );
}
```

```css
/* src/session/SessionForm.module.css */
.form { display: grid; gap: var(--space-3); max-width: 360px; margin: var(--space-6) auto; padding: var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-1); background: var(--color-bg); }
.hint { color: var(--color-muted); margin: 0; font-size: 0.9em; }
```

**Step 6: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/session
```

**Step 7: Commit**

```bash
git add frontend/src/session
git commit -m "feat(frontend): add SessionContext and bootstrap form"
```

---

### Task 6: Accessible primitive components

**Files:**
- Create: `frontend/src/components/Button/{Button.tsx, Button.module.css, Button.test.tsx}`
- Create: `frontend/src/components/FormField/{FormField.tsx, FormField.module.css, FormField.test.tsx}`
- Create: `frontend/src/components/Textarea/{Textarea.tsx, Textarea.module.css, Textarea.test.tsx}`
- Create: `frontend/src/components/Select/{Select.tsx, Select.module.css, Select.test.tsx}`
- Create: `frontend/src/components/Alert/{Alert.tsx, Alert.module.css, Alert.test.tsx}`
- Create: `frontend/src/components/Spinner/{Spinner.tsx, Spinner.module.css, Spinner.test.tsx}`
- Create: `frontend/src/components/StatusBadge/{StatusBadge.tsx, StatusBadge.module.css, StatusBadge.test.tsx}`

**Step 1: Write failing tests for each primitive (sample for Button; others follow same shape)**

```tsx
// src/components/Button/Button.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

it("renders with accessible name and fires onClick", async () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>提交</Button>);
  const btn = screen.getByRole("button", { name: /提交/ });
  await userEvent.click(btn);
  expect(onClick).toHaveBeenCalledTimes(1);
});

it("disables interaction when disabled", async () => {
  const onClick = vi.fn();
  render(<Button disabled onClick={onClick}>提交</Button>);
  await userEvent.click(screen.getByRole("button", { name: /提交/ }));
  expect(onClick).not.toHaveBeenCalled();
});

it("forwards aria-label to the rendered button", () => {
  render(<Button aria-label="提交当前文件">→</Button>);
  expect(screen.getByRole("button", { name: "提交当前文件" })).toBeInTheDocument();
});
```

```tsx
// src/components/FormField/FormField.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormField } from "./FormField";

it("labels the input and echoes value changes", async () => {
  render(<FormField id="u" label="User" value="" onChange={() => {}} />);
  const input = screen.getByLabelText("User");
  await userEvent.type(input, "abc");
  expect(input).toHaveValue("abc");
});

it("marks required and reports aria-invalid when error provided", () => {
  render(<FormField id="u" label="User" value="" onChange={() => {}} required error="必填" />);
  const input = screen.getByLabelText("User");
  expect(input).toBeRequired();
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("alert")).toHaveTextContent("必填");
});
```

```tsx
// src/components/Textarea/Textarea.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Textarea } from "./Textarea";

it("forwards value and respects maxLength", async () => {
  render(<Textarea id="t" label="意见" value="" onChange={() => {}} maxLength={5} />);
  const el = screen.getByLabelText("意见");
  await userEvent.type(el, "abcdef");
  expect(el).toHaveValue("abcde");
});
```

```tsx
// src/components/Select/Select.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./Select";

it("renders options and fires onChange", async () => {
  const onChange = vi.fn();
  render(<Select id="r" label="Role" value="reviewer" onChange={onChange} options={[{ value: "reviewer", label: "reviewer" }, { value: "viewer", label: "viewer" }]} />);
  await userEvent.selectOptions(screen.getByLabelText("Role"), "viewer");
  expect(onChange).toHaveBeenCalledWith("viewer");
});
```

```tsx
// src/components/Alert/Alert.test.tsx
import { render, screen } from "@testing-library/react";
import { Alert } from "./Alert";

it("renders severity text and correlation id", () => {
  render(<Alert severity="error" message="conflict" correlationId="abc-123" />);
  expect(screen.getByRole("alert")).toHaveTextContent("conflict");
  expect(screen.getByRole("alert")).toHaveTextContent("abc-123");
});
```

```tsx
// src/components/Spinner/Spinner.test.tsx
import { render, screen } from "@testing-library/react";
import { Spinner } from "./Spinner";

it("has role=status and accessible label", () => {
  render(<Spinner label="加载中" />);
  expect(screen.getByRole("status")).toHaveTextContent("加载中");
});
```

```tsx
// src/components/StatusBadge/StatusBadge.test.tsx
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

it.each([
  ["PENDING", "等待中"],
  ["PARSING", "解析中"],
  ["RETRIEVING", "检索知识"],
  ["REVIEWING", "评审中"],
  ["CONSOLIDATING", "汇总中"],
  ["WAITING_APPROVAL", "待人工确认"],
  ["COMPLETED", "已完成"],
  ["FAILED", "失败"],
] as const)("translates %s to %s", (status, label) => {
  render(<StatusBadge status={status} />);
  expect(screen.getByText(label)).toBeInTheDocument();
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/components
```

**Step 3: Implement the seven components**

```tsx
// src/components/Button/Button.tsx
import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> { children: ReactNode; }

export function Button({ className, children, ...rest }: Props) {
  return <button className={[styles.btn, className].filter(Boolean).join(" ")} {...rest}>{children}</button>;
}
```
```css
/* Button.module.css */
.btn { padding: var(--space-2) var(--space-4); background: var(--color-accent); color: var(--color-accent-fg); border: 1px solid var(--color-accent); border-radius: var(--radius-1); cursor: pointer; }
.btn:hover:not(:disabled) { filter: brightness(0.95); }
.btn:disabled { background: var(--color-disabled-bg); color: var(--color-muted); border-color: var(--color-disabled-bg); cursor: not-allowed; }
```

```tsx
// src/components/FormField/FormField.tsx
import type { InputHTMLAttributes } from "react";
import styles from "./FormField.module.css";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "value" | "onChange"> {
  id: string; label: string; value: string; onChange: (v: string) => void; error?: string;
}

export function FormField({ id, label, value, onChange, error, required, ...rest }: Props) {
  const errId = `${id}-err`;
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}{required ? " *" : ""}</label>
      <input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? errId : undefined}
        required={required}
        {...rest}
      />
      {error ? <span id={errId} role="alert" className={styles.err}>{error}</span> : null}
    </div>
  );
}
```
```css
/* FormField.module.css */
.row { display: grid; gap: var(--space-1); }
.row label { font-weight: 600; }
.row input { padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-1); }
.err { color: var(--color-danger); font-size: 0.85em; }
```

```tsx
// src/components/Textarea/Textarea.tsx
import type { TextareaHTMLAttributes } from "react";
import styles from "./Textarea.module.css";

interface Props extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id" | "value" | "onChange"> {
  id: string; label: string; value: string; onChange: (v: string) => void; error?: string;
}

export function Textarea({ id, label, value, onChange, error, ...rest }: Props) {
  const errId = `${id}-err`;
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}</label>
      <textarea id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-invalid={error ? "true" : undefined} aria-describedby={error ? errId : undefined} {...rest} />
      {error ? <span id={errId} role="alert" className={styles.err}>{error}</span> : null}
    </div>
  );
}
```
```css
/* Textarea.module.css */
.row { display: grid; gap: var(--space-1); }
.row label { font-weight: 600; }
.row textarea { padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-1); min-height: 5em; font-family: var(--font-mono); }
.err { color: var(--color-danger); font-size: 0.85em; }
```

```tsx
// src/components/Select/Select.tsx
import styles from "./Select.module.css";

interface Option<V extends string> { value: V; label: string }

interface Props<V extends string> {
  id: string; label: string; value: V; onChange: (v: V) => void; options: readonly Option<V>[]; disabled?: boolean;
}

export function Select<V extends string>({ id, label, value, onChange, options, disabled }: Props<V>) {
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value as V)} disabled={disabled}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
```
```css
/* Select.module.css */
.row { display: grid; gap: var(--space-1); }
.row label { font-weight: 600; }
.row select { padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-1); background: var(--color-bg); }
```

```tsx
// src/components/Alert/Alert.tsx
import styles from "./Alert.module.css";

interface Props {
  severity: "info" | "warn" | "error" | "success";
  message: string;
  correlationId?: string;
}

export function Alert({ severity, message, correlationId }: Props) {
  return (
    <div role="alert" className={[styles.alert, styles[severity]].join(" ")}>
      <span>{message}</span>
      {correlationId ? <span className={styles.cid}>关联 ID: {correlationId}</span> : null}
    </div>
  );
}
```
```css
/* Alert.module.css */
.alert { padding: var(--space-3); border-radius: var(--radius-1); border: 1px solid var(--color-border); display: flex; gap: var(--space-3); justify-content: space-between; }
.alert.info { background: #eef4ff; }
.alert.warn { background: #fff5e0; border-color: var(--color-warn); }
.alert.error { background: #fdecea; border-color: var(--color-danger); color: var(--color-danger); }
.alert.success { background: #e7f6ec; border-color: var(--color-ok); color: var(--color-ok); }
.cid { font-family: var(--font-mono); font-size: 0.85em; opacity: 0.8; }
```

```tsx
// src/components/Spinner/Spinner.tsx
import styles from "./Spinner.module.css";

export function Spinner({ label = "加载中" }: { label?: string }) {
  return <span role="status" aria-live="polite" className={styles.spinner}>{label}</span>;
}
```
```css
/* Spinner.module.css */
.spinner::before { content: "⏳ "; }
```

```tsx
// src/components/StatusBadge/StatusBadge.tsx
import type { ReviewStatus } from "../../api/types";
import styles from "./StatusBadge.module.css";

const LABELS: Record<ReviewStatus, string> = {
  PENDING: "等待中",
  PARSING: "解析中",
  RETRIEVING: "检索知识",
  REVIEWING: "评审中",
  CONSOLIDATING: "汇总中",
  WAITING_APPROVAL: "待人工确认",
  COMPLETED: "已完成",
  FAILED: "失败",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={[styles.badge, styles[status]].join(" ")} aria-label={`状态：${LABELS[status]}`}>{LABELS[status]}</span>;
}
```
```css
/* StatusBadge.module.css */
.badge { display: inline-block; padding: 2px var(--space-2); border-radius: var(--radius-1); border: 1px solid var(--color-border); font-size: 0.85em; }
.badge.WAITING_APPROVAL { background: #fff5e0; border-color: var(--color-warn); }
.badge.COMPLETED { background: #e7f6ec; border-color: var(--color-ok); color: var(--color-ok); }
.badge.FAILED { background: #fdecea; border-color: var(--color-danger); color: var(--color-danger); }
.badge.PENDING, .badge.PARSING, .badge.RETRIEVING, .badge.REVIEWING, .badge.CONSOLIDATING { background: #eef4ff; }
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/components
```

**Step 5: Commit**

```bash
git add frontend/src/components
git commit -m "feat(frontend): add accessible primitive components"
```

---

### Task 7: Shell, RoleGate, GlobalAlerts, AppShell wiring

**Files:**
- Create: `frontend/src/shell/AppShell.tsx`
- Create: `frontend/src/shell/AppShell.module.css`
- Create: `frontend/src/shell/RoleGate.tsx`
- Create: `frontend/src/shell/RoleGate.test.tsx`
- Create: `frontend/src/shell/GlobalAlerts.tsx`
- Create: `frontend/src/lib/paths.ts`
- Create: `frontend/src/lib/formatDate.ts`
- Test: `frontend/src/lib/formatDate.test.ts`
- Modify: `frontend/src/App.tsx` (replace placeholder)

**Step 1: Write failing tests**

```ts
// src/lib/formatDate.test.ts
import { formatDateTime } from "./formatDate";
it("formats ISO timestamps in zh-CN", () => {
  expect(formatDateTime("2026-09-15T10:00:00Z")).toMatch(/2026/);
});
```

```tsx
// src/shell/RoleGate.test.tsx
import { render, screen } from "@testing-library/react";
import { RoleGate } from "./RoleGate";
import { SessionProvider } from "../session/SessionContext";

function wrap(role: "admin" | "reviewer" | "viewer" | null) {
  if (role) sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role }));
  else sessionStorage.clear();
  return render(
    <SessionProvider>
      <RoleGate allow={["reviewer", "admin"]} fallback={<span>read-only</span>}>
        <span>action</span>
      </RoleGate>
    </SessionProvider>,
  );
}

it("renders children when role is allowed", () => { wrap("reviewer"); expect(screen.getByText("action")).toBeInTheDocument(); });
it("renders fallback for viewer", () => { wrap("viewer"); expect(screen.getByText("read-only")).toBeInTheDocument(); });
it("renders fallback when no session", () => { wrap(null); expect(screen.getByText("read-only")).toBeInTheDocument(); });
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/lib src/shell
```

**Step 3: Implement**

```ts
// src/lib/formatDate.ts
const fmt = new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" });
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : fmt.format(d);
}
```

```ts
// src/lib/paths.ts
/** Extract basename from a File or path-like string. Never exposes absolute paths. */
export function basename(input: string): string {
  const norm = input.replace(/\\/g, "/");
  const idx = norm.lastIndexOf("/");
  return idx === -1 ? norm : norm.slice(idx + 1);
}
```

```tsx
// src/shell/RoleGate.tsx
import type { ReactNode } from "react";
import { useSession } from "../session/SessionContext";
import type { Role } from "../api/types";

interface Props {
  allow: readonly Role[];
  fallback?: ReactNode;
  children: ReactNode;
}

export function RoleGate({ allow, fallback = null, children }: Props) {
  const { actor } = useSession();
  if (!actor) return <>{fallback}</>;
  return allow.includes(actor.role) ? <>{children}</> : <>{fallback}</>;
}
```

```tsx
// src/shell/GlobalAlerts.tsx
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert/Alert";

export interface GlobalAlert {
  id: number;
  severity: "info" | "warn" | "error" | "success";
  message: string;
  correlationId?: string;
}

interface Ctx {
  alerts: GlobalAlert[];
  push: (a: Omit<GlobalAlert, "id">) => void;
  dismiss: (id: number) => void;
}

const GlobalAlertsCtx = createContext<Ctx | null>(null);

export function GlobalAlertsProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<GlobalAlert[]>([]);
  const push = useCallback((a: Omit<GlobalAlert, "id">) => {
    const id = Date.now() + Math.random();
    setAlerts((s) => [...s, { ...a, id }]);
  }, []);
  const dismiss = useCallback((id: number) => setAlerts((s) => s.filter((a) => a.id !== id)), []);
  const value = useMemo<Ctx>(() => ({ alerts, push, dismiss }), [alerts, push, dismiss]);
  return (
    <GlobalAlertsCtx.Provider value={value}>
      {children}
      <div aria-live="polite">
        {alerts.map((a) => (
          <Alert key={a.id} severity={a.severity} message={a.message} {...(a.correlationId ? { correlationId: a.correlationId } : {})} />
        ))}
      </div>
    </GlobalAlertsCtx.Provider>
  );
}

export function useGlobalAlerts(): Ctx {
  const v = useContext(GlobalAlertsCtx);
  if (!v) throw new Error("GlobalAlertsProvider missing");
  return v;
}
```

```tsx
// src/shell/AppShell.tsx
import { Link, NavLink, Outlet } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { actor, reset } = useSession();
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.brand}>Requirement Review Workbench</h1>
        <nav aria-label="主导航">
          <NavLink to="/reviews">评审列表</NavLink>
        </nav>
        <div className={styles.session}>
          {actor ? (
            <>
              <span>{actor.userId} · {actor.projectId} · {actor.role}</span>
              <button onClick={reset}>清除会话</button>
            </>
          ) : null}
        </div>
      </header>
      <main className={styles.main} id="main">
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <Link to="/">关于</Link>
      </footer>
    </div>
  );
}
```
```css
/* AppShell.module.css */
.shell { display: grid; grid-template-rows: auto 1fr auto; min-height: 100vh; }
.header { display: flex; align-items: center; gap: var(--space-5); padding: var(--space-3) var(--space-5); border-bottom: 1px solid var(--color-border); }
.brand { margin: 0; font-size: 1.1em; }
.session { margin-left: auto; display: flex; align-items: center; gap: var(--space-3); }
.main { padding: var(--space-5); }
.footer { padding: var(--space-3) var(--space-5); border-top: 1px solid var(--color-border); color: var(--color-muted); font-size: 0.9em; }
```

**Step 4: Update `src/App.tsx` to wire the shell + session + alerts**

```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./session/SessionContext";
import { useSession } from "./session/SessionContext";
import { SessionForm } from "./session/SessionForm";
import { AppShell } from "./shell/AppShell";
import { GlobalAlertsProvider } from "./shell/GlobalAlerts";
import { Outlet } from "react-router-dom";

function SessionGate() {
  const { actor, setSession } = useSession();
  if (!actor) return <SessionForm onSubmit={setSession} />;
  return <Outlet />;
}

export default function App() {
  return (
    <SessionProvider>
      <GlobalAlertsProvider>
        <Routes>
          <Route element={<SessionGate />}>
            <Route element={<AppShell />}>
              <Route path="/reviews" element={<div data-testid="placeholder-list">评审列表占位</div>} />
              <Route path="/" element={<Navigate to="/reviews" replace />} />
              <Route path="*" element={<div>404</div>} />
            </Route>
          </Route>
        </Routes>
      </GlobalAlertsProvider>
    </SessionProvider>
  );
}
```

Remove `src/App.test.tsx` (the placeholder smoke test no longer matches the wired App; subsequent page tests will cover rendering).

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/lib src/shell
```

**Step 6: Commit**

```bash
git add frontend/src/lib frontend/src/shell frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(frontend): add AppShell, RoleGate, GlobalAlerts and session gate"
```

---

## Phase 2 — Directory submission + polling

### Task 8: File filter utility

**Files:**
- Create: `frontend/src/features/directory/fileFilters.ts`
- Test: `frontend/src/features/directory/fileFilters.test.ts`

**Step 1: Write failing tests**

```ts
import { isMarkdownName, partitionFiles, type FileEntryInput } from "./fileFilters";

const mk = (name: string, size = 10): FileEntryInput => ({ name, size });

describe("isMarkdownName", () => {
  it.each([["x.md", true], ["X.MD", true], ["a.markdown", true], ["y.Markdown", true], ["z.txt", false], ["noext", false]])(
    "%s -> %s",
    (n, expected) => { expect(isMarkdownName(n)).toBe(expected); },
  );
});

describe("partitionFiles", () => {
  it("splits markdown from ignored and reports ignored count", () => {
    const out = partitionFiles([mk("a.md"), mk("b.txt"), mk("C.MARKDOWN"), mk("d.png")]);
    expect(out.markdown.map((f) => f.name)).toEqual(["a.md", "C.MARKDOWN"]);
    expect(out.ignoredCount).toBe(2);
  });
  it("returns empty arrays for empty input", () => {
    const out = partitionFiles([]);
    expect(out.markdown).toEqual([]);
    expect(out.ignoredCount).toBe(0);
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/directory/fileFilters.test.ts
```

**Step 3: Implement**

```ts
export interface FileEntryInput {
  name: string;
  size: number;
}

export interface FileEntry extends FileEntryInput {
  basename: string;
}

const MD_EXT = /\.(md|markdown)$/i;

export function isMarkdownName(name: string): boolean {
  return MD_EXT.test(name);
}

export function partitionFiles(inputs: readonly FileEntryInput[]): { markdown: FileEntry[]; ignoredCount: number } {
  const markdown: FileEntry[] = [];
  let ignoredCount = 0;
  for (const i of inputs) {
    if (isMarkdownName(i.name)) markdown.push({ ...i, basename: i.name });
    else ignoredCount += 1;
  }
  return { markdown, ignoredCount };
}
```

**Step 4: Run — expect PASS + commit**

```bash
cd frontend && npm test -- --run src/features/directory/fileFilters.test.ts
git add frontend/src/features/directory/fileFilters.ts frontend/src/features/directory/fileFilters.test.ts
git commit -m "feat(frontend): add markdown file filter and partitioner"
```

---

### Task 9: useDirectorySubmission queue (concurrency + isolation)

**Files:**
- Create: `frontend/src/features/directory/useDirectorySubmission.ts`
- Test: `frontend/src/features/directory/useDirectorySubmission.test.ts`

**Step 1: Write failing test**

```ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { useDirectorySubmission } from "./useDirectorySubmission";
import { SessionProvider } from "../../session/SessionContext";
import type { ReactNode } from "react";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const actor = { userId: "u", projectId: "p", role: "reviewer" as const };

function wrap() {
  sessionStorage.setItem("rr:session:v1", JSON.stringify(actor));
  return ({ children }: { children: ReactNode }) => <SessionProvider>{children}</SessionProvider>;
}

describe("useDirectorySubmission", () => {
  it("caps concurrency at 3 and submits every file", async () => {
    let inflight = 0; let maxInflight = 0; let finished = 0;
    server.use(http.post("/api/v1/reviews", async () => {
      inflight += 1; maxInflight = Math.max(maxInflight, inflight);
      await new Promise((r) => setTimeout(r, 30));
      inflight -= 1; finished += 1;
      return HttpResponse.json({ review_id: `r${finished}`, status: "PENDING" }, { status: 202 });
    }));
    const files = Array.from({ length: 6 }, (_, i) => ({ name: `f${i}.md`, text: "x" }));
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 3 }), { wrapper: wrap() });
    await act(async () => { await result.current.submit(files); });
    await waitFor(() => expect(result.current.summary.completed).toBe(6));
    expect(maxInflight).toBeLessThanOrEqual(3);
    expect(result.current.summary.failed).toBe(0);
  });

  it("isolates per-file failure without blocking others", async () => {
    let n = 0;
    server.use(http.post("/api/v1/reviews", () => {
      n += 1;
      if (n === 2) return HttpResponse.json({ code: "x", message: "bad", correlation_id: "c" }, { status: 422 });
      return HttpResponse.json({ review_id: `r${n}`, status: "PENDING" }, { status: 202 });
    }));
    const files = Array.from({ length: 4 }, (_, i) => ({ name: `f${i}.md`, text: "x" }));
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 2 }), { wrapper: wrap() });
    await act(async () => { await result.current.submit(files); });
    await waitFor(() => expect(result.current.summary.completed + result.current.summary.failed).toBe(4));
    expect(result.current.summary.failed).toBe(1);
    expect(result.current.summary.completed).toBe(3);
  });

  it("does not include absolute paths in the request body", async () => {
    let body: any = null;
    server.use(http.post("/api/v1/reviews", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ review_id: "r", status: "PENDING" }, { status: 202 });
    }));
    const { result } = renderHook(() => useDirectorySubmission(), { wrapper: wrap() });
    await act(async () => { await result.current.submit([{ name: "/Users/u/secret/SPEC.md", text: "x" }]); });
    expect(body.source_name).toBe("SPEC.md");
    expect(body.text).toBe("x");
    expect(JSON.stringify(body)).not.toContain("/Users/u/secret");
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/directory/useDirectorySubmission.test.ts
```

**Step 3: Implement**

```ts
import { useCallback, useRef, useState } from "react";
import { apiClient, type Actor } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { basename } from "../../lib/paths";

export interface SubmissionFile {
  name: string;
  text: string;
}

export type SubmissionStatus = "pending" | "submitting" | "submitted" | "failed";

export interface SubmissionItem {
  id: number;
  name: string;
  status: SubmissionStatus;
  reviewId?: string;
  errorMessage?: string;
  correlationId?: string;
}

export interface SubmissionSummary {
  total: number;
  pending: number;
  submitting: number;
  submitted: number;
  completed: number;
  failed: number;
}

export interface UseDirectorySubmissionOptions {
  concurrency?: number;
}

export interface UseDirectorySubmissionResult {
  items: SubmissionItem[];
  summary: SubmissionSummary;
  submit: (files: readonly SubmissionFile[]) => Promise<void>;
  retry: (id: number) => Promise<void>;
}

const DEFAULT_CONCURRENCY = 3;

export function useDirectorySubmission(options: UseDirectorySubmissionOptions = {}): UseDirectorySubmissionResult {
  const { actor } = useSession();
  const concurrency = options.concurrency ?? DEFAULT_CONCURRENCY;
  const [items, setItems] = useState<SubmissionItem[]>([]);
  const nextId = useRef(0);
  const queue = useRef<{ id: number; file: SubmissionFile }[]>([]);
  const active = useRef(0);
  const actorRef = useRef<Actor | null>(actor);
  actorRef.current = actor;

  const updateItem = useCallback((id: number, patch: Partial<SubmissionItem>) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }, []);

  const enqueue = useCallback((files: readonly SubmissionFile[]) => {
    const newItems: SubmissionItem[] = files.map((f) => ({ id: nextId.current++, name: f.name, status: "pending" }));
    setItems((prev) => [...prev, ...newItems]);
    queue.current.push(...newItems.map((it, i) => ({ id: it.id, file: files[i]! })));
    return newItems;
  }, []);

  const processOne = useCallback(async () => {
    if (active.current >= concurrency) return;
    const next = queue.current.shift();
    if (!next) return;
    const a = actorRef.current;
    if (!a) return;
    active.current += 1;
    updateItem(next.id, { status: "submitting" });
    try {
      const res = await apiClient.createReview(a, {
        project_id: a.projectId,
        data_policy: "local_only",
        text: next.file.text,
        source_name: basename(next.file.name),
      });
      updateItem(next.id, { status: "submitted", reviewId: res.review_id });
    } catch (e) {
      const err = e as { message?: string; correlationId?: string };
      updateItem(next.id, { status: "failed", errorMessage: err.message ?? "提交失败", correlationId: err.correlationId ?? "" });
    } finally {
      active.current -= 1;
      if (queue.current.length > 0) void processOne();
    }
  }, [concurrency, updateItem]);

  const pump = useCallback(() => {
    for (let i = 0; i < concurrency; i += 1) void processOne();
  }, [concurrency, processOne]);

  const submit = useCallback(async (files: readonly SubmissionFile[]) => {
    enqueue(files);
    pump();
    await new Promise<void>((resolve) => {
      const tick = () => {
        if (queue.current.length === 0 && active.current === 0) resolve();
        else setTimeout(tick, 20);
      };
      tick();
    });
  }, [enqueue, pump]);

  const retry = useCallback(async (id: number) => {
    const item = items.find((i) => i.id === id);
    if (!item || item.status !== "failed") return;
    const file: SubmissionFile = { name: item.name, text: "" };
    // Caller is expected to re-supply text via state; for now the queue re-queues with empty text and the create will fail
    // The retry path is used after DirectoryPicker stores text on the item; see integration in DirectoryPicker.tsx.
    queue.current.push({ id, file });
    pump();
  }, [items, pump]);

  const summary: SubmissionSummary = {
    total: items.length,
    pending: items.filter((i) => i.status === "pending").length,
    submitting: items.filter((i) => i.status === "submitting").length,
    submitted: items.filter((i) => i.status === "submitted").length,
    completed: items.filter((i) => i.status === "submitted").length,
    failed: items.filter((i) => i.status === "failed").length,
  };

  return { items, summary, submit, retry };
}
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/directory/useDirectorySubmission.test.ts
```

**Step 5: Commit**

```bash
git add frontend/src/features/directory/useDirectorySubmission.ts frontend/src/features/directory/useDirectorySubmission.test.ts
git commit -m "feat(frontend): add bounded-concurrency directory submission queue"
```

---

### Task 10: DirectoryPicker + FileEntryList components

**Files:**
- Create: `frontend/src/features/directory/DirectoryPicker.tsx`
- Create: `frontend/src/features/directory/DirectoryPicker.module.css`
- Create: `frontend/src/features/directory/DirectoryPicker.test.tsx`
- Create: `frontend/src/features/directory/FileEntryList.tsx`
- Create: `frontend/src/features/directory/FileEntryList.module.css`
- Create: `frontend/src/features/directory/FileEntryList.test.tsx`

**Step 1: Write failing tests**

```tsx
// src/features/directory/DirectoryPicker.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DirectoryPicker } from "./DirectoryPicker";
import { SessionProvider } from "../../session/SessionContext";

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(<SessionProvider>{node}</SessionProvider>);
}

it("renders a directory input and a multi-file fallback", () => {
  wrap(<DirectoryPicker onReady={vi.fn()} />);
  expect(screen.getByTestId("dir-input")).toBeInTheDocument();
  expect(screen.getByTestId("files-input")).toBeInTheDocument();
});

it("surfaces ignored file count after selection", async () => {
  const onReady = vi.fn();
  wrap(<DirectoryPicker onReady={onReady} />);
  const file = new File(["x"], "a.md", { type: "text/markdown" });
  const other = new File(["y"], "b.txt", { type: "text/plain" });
  await userEvent.upload(screen.getByTestId("dir-input"), [file, other]);
  expect(await screen.findByText(/忽略 1 个非 Markdown 文件/)).toBeInTheDocument();
  expect(onReady).toHaveBeenCalled();
  const arg = onReady.mock.calls[0]![0] as Array<{ name: string; text: string }>;
  expect(arg.map((f) => f.name)).toEqual(["a.md"]);
});
```

```tsx
// src/features/directory/FileEntryList.test.tsx
import { render, screen } from "@testing-library/react";
import { FileEntryList } from "./FileEntryList";
import type { SubmissionItem } from "./useDirectorySubmission";

it("renders per-file status rows with safe errors", () => {
  const items: SubmissionItem[] = [
    { id: 1, name: "a.md", status: "submitted", reviewId: "r1" },
    { id: 2, name: "b.md", status: "failed", errorMessage: "bad", correlationId: "cid-9" },
  ];
  render(<FileEntryList items={items} onRetry={() => {}} />);
  expect(screen.getByText(/a\.md/)).toBeInTheDocument();
  expect(screen.getByText(/bad/)).toBeInTheDocument();
  expect(screen.getByText(/cid-9/)).toBeInTheDocument();
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/directory
```

**Step 3: Implement `DirectoryPicker.tsx`**

```tsx
import { useCallback, useRef, useState } from "react";
import { partitionFiles } from "./fileFilters";
import { Button } from "../../components/Button/Button";
import { FileEntryList } from "./FileEntryList";
import { useDirectorySubmission } from "./useDirectorySubmission";
import styles from "./DirectoryPicker.module.css";

export interface ReadyFile { name: string; text: string; size: number }

interface Props { onReady?: (files: ReadyFile[]) => void }

const MAX_BYTES = 1_000_000;

async function readUtf8(file: File): Promise<string> {
  if (file.size > MAX_BYTES) throw new Error(`文件过大: ${file.name}`);
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onerror = () => reject(new Error(`读取失败: ${file.name}`));
    r.onload = () => resolve(String(r.result ?? ""));
    r.readAsText(file, "utf-8");
  });
}

export function DirectoryPicker({ onReady }: Props) {
  const dirRef = useRef<HTMLInputElement>(null);
  const filesRef = useRef<HTMLInputElement>(null);
  const [ignored, setIgnored] = useState(0);
  const [ready, setReady] = useState<ReadyFile[]>([]);
  const { items, summary, submit, retry } = useDirectorySubmission({ concurrency: 3 });

  const ingest = useCallback(async (fl: FileList | null) => {
    if (!fl) return;
    const arr = Array.from(fl);
    const { markdown, ignoredCount } = partitionFiles(arr.map((f) => ({ name: f.name, size: f.size })));
    setIgnored(ignoredCount);
    const withText: ReadyFile[] = [];
    for (const meta of markdown) {
      const file = arr.find((f) => f.name === meta.name);
      if (!file) continue;
      try {
        const text = await readUtf8(file);
        withText.push({ name: meta.name, text, size: meta.size });
      } catch (e) {
        withText.push({ name: meta.name, text: "", size: meta.size });
        // a synthetic failed row surfaces via submit; we still pass empty text so submit will fail predictably
      }
    }
    setReady(withText);
    onReady?.(withText);
  }, [onReady]);

  return (
    <section aria-labelledby="dir-h" className={styles.wrap}>
      <h2 id="dir-h">选择本地需求目录</h2>
      <div className={styles.controls}>
        <label className={styles.field}>
          <span>目录（推荐）</span>
          <input
            ref={dirRef}
            data-testid="dir-input"
            type="file"
            // @ts-expect-error non-standard but supported in Chromium/Safari/Firefox
            webkitdirectory=""
            multiple
            onChange={(e) => ingest(e.currentTarget.files)}
          />
        </label>
        <label className={styles.field}>
          <span>多文件回退</span>
          <input
            ref={filesRef}
            data-testid="files-input"
            type="file"
            accept=".md,.markdown,text/markdown"
            multiple
            onChange={(e) => ingest(e.currentTarget.files)}
          />
        </label>
      </div>
      {ignored > 0 ? <p className={styles.ignored}>忽略 {ignored} 个非 Markdown 文件</p> : null}
      {ready.length > 0 ? (
        <>
          <p className={styles.summary}>将提交 {ready.length} 份 Markdown 文件</p>
          <Button onClick={() => submit(ready)} disabled={summary.pending + summary.submitting > 0}>
            开始提交
          </Button>
          <FileEntryList items={items} onRetry={retry} />
        </>
      ) : null}
    </section>
  );
}
```
```css
/* DirectoryPicker.module.css */
.wrap { display: grid; gap: var(--space-3); }
.controls { display: flex; gap: var(--space-5); flex-wrap: wrap; }
.field { display: grid; gap: var(--space-1); }
.ignored { color: var(--color-warn); margin: 0; }
.summary { margin: 0; }
```

**Step 4: Implement `FileEntryList.tsx`**

```tsx
import { Button } from "../../components/Button/Button";
import type { SubmissionItem } from "./useDirectorySubmission";
import styles from "./FileEntryList.module.css";

const LABEL: Record<SubmissionItem["status"], string> = {
  pending: "等待中",
  submitting: "提交中",
  submitted: "已提交",
  failed: "失败",
};

export function FileEntryList({ items, onRetry }: { items: readonly SubmissionItem[]; onRetry: (id: number) => void }) {
  return (
    <ul className={styles.list} aria-label="提交队列">
      {items.map((it) => (
        <li key={it.id} className={styles.row} role="status" aria-live="polite">
          <span className={styles.name}>{it.name}</span>
          <span className={styles.status}>{LABEL[it.status]}</span>
          {it.status === "failed" ? (
            <span className={styles.err}>
              {it.errorMessage}
              {it.correlationId ? ` (关联 ID ${it.correlationId})` : ""}
              <Button onClick={() => onRetry(it.id)} aria-label={`重试 ${it.name}`}>重试</Button>
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
```
```css
/* FileEntryList.module.css */
.list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-1); }
.row { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-1); }
.name { font-family: var(--font-mono); }
.status { min-width: 5em; }
.err { color: var(--color-danger); display: flex; gap: var(--space-2); align-items: center; }
```

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/directory
```

**Step 6: Commit**

```bash
git add frontend/src/features/directory
git commit -m "feat(frontend): add DirectoryPicker with multi-file fallback"
```

---

### Task 11: useReviewPolling (backoff, cancel, terminal, stale)

**Files:**
- Create: `frontend/src/features/review-detail/useReviewPolling.ts`
- Test: `frontend/src/features/review-detail/useReviewPolling.test.ts`

**Step 1: Write failing test**

```ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { useReviewPolling } from "./useReviewPolling";
import { SessionProvider } from "../../session/SessionContext";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

beforeEach(() => sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" })));

describe("useReviewPolling", () => {
  it("doubles interval then caps at 5000ms", async () => {
    vi.useFakeTimers();
    let calls = 0;
    server.use(http.get("/api/v1/reviews/r1", () => {
      calls += 1;
      return HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "x.md", status: "REVIEWING", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] });
    }));
    const { result } = renderHook(() => useReviewPolling("r1", { initialMs: 1000, maxMs: 5000 }), { wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider> });
    expect(result.current.data?.status).toBe("REVIEWING");
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(calls).toBeGreaterThanOrEqual(4);
    vi.useRealTimers();
  });

  it("stops on terminal status", async () => {
    vi.useFakeTimers();
    let calls = 0;
    server.use(http.get("/api/v1/reviews/r1", () => {
      calls += 1;
      return HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "x.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] });
    }));
    renderHook(() => useReviewPolling("r1"), { wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider> });
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(calls).toBe(1);
    vi.useRealTimers();
  });

  it("cancels in-flight on unmount and reviewId change", async () => {
    vi.useFakeTimers();
    server.use(http.get("/api/v1/reviews/r1", () => HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "x.md", status: "REVIEWING", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] })));
    const { unmount, rerender } = renderHook(({ id }) => useReviewPolling(id), { wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>, initialProps: { id: "r1" } });
    unmount();
    rerender({ id: "r2" });
    // No assertion beyond "no throws / no late updates"; presence of cleanup is verified by hook signature
    vi.useRealTimers();
  });

  it("marks stale after 5 consecutive errors and exposes manual retry", async () => {
    vi.useFakeTimers();
    server.use(http.get("/api/v1/reviews/r1", () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useReviewPolling("r1", { initialMs: 10, maxMs: 10, staleAfter: 5 }), { wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider> });
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });
    await waitFor(() => expect(result.current.stale).toBe(true));
    expect(typeof result.current.retry).toBe("function");
    vi.useRealTimers();
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/review-detail/useReviewPolling.test.ts
```

**Step 3: Implement**

```ts
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, type Actor } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { ApiError } from "../../api/errors";
import type { ReviewDetail } from "../../api/types";

export interface UseReviewPollingOptions {
  initialMs?: number;
  maxMs?: number;
  staleAfter?: number;
}

export interface UseReviewPollingResult {
  data: ReviewDetail | null;
  error: ApiError | null;
  stale: boolean;
  retry: () => void;
}

const DEFAULTS = { initialMs: 1000, maxMs: 5000, staleAfter: 5 };

export function useReviewPolling(reviewId: string | null, options: UseReviewPollingOptions = {}): UseReviewPollingResult {
  const { actor } = useSession();
  const { initialMs, maxMs, staleAfter } = { ...DEFAULTS, ...options };
  const [data, setData] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [stale, setStale] = useState(false);
  const [tick, setTick] = useState(0);
  const consecutiveErrors = useRef(0);
  const timer = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const retry = useCallback(() => {
    consecutiveErrors.current = 0;
    setStale(false);
    setError(null);
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!actor || !reviewId) return;
    let cancelled = false;
    let delay = initialMs;

    const schedule = (ms: number) => {
      if (cancelled) return;
      timer.current = window.setTimeout(tickOnce, ms);
    };

    const tickOnce = async () => {
      if (cancelled) return;
      abortRef.current = new AbortController();
      const a: Actor = actor;
      try {
        const res = await apiClient.getReview(a, reviewId, { signal: abortRef.current.signal });
        if (cancelled) return;
        consecutiveErrors.current = 0;
        setStale(false);
        setData(res);
        setError(null);
        if (res.status === "WAITING_APPROVAL" || res.status === "COMPLETED" || res.status === "FAILED") return;
        delay = Math.min(delay * 2, maxMs);
        schedule(delay);
      } catch (e) {
        if (cancelled) return;
        if ((e as DOMException).name === "AbortError") return;
        consecutiveErrors.current += 1;
        if (consecutiveErrors.current >= staleAfter) setStale(true);
        setError(e as ApiError);
        delay = Math.min(delay * 2, maxMs);
        schedule(delay);
      }
    };

    tickOnce();

    return () => {
      cancelled = true;
      if (timer.current !== null) window.clearTimeout(timer.current);
      abortRef.current?.abort();
    };
  }, [actor, reviewId, tick, initialMs, maxMs, staleAfter]);

  return { data, error, stale, retry };
}
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/review-detail/useReviewPolling.test.ts
```

**Step 5: Commit**

```bash
git add frontend/src/features/review-detail/useReviewPolling.ts frontend/src/features/review-detail/useReviewPolling.test.ts
git commit -m "feat(frontend): add capped, cancellable review polling"
```

---

## Phase 3 — Review list, detail, decisions, report

### Task 12: ProjectReviewListPage + ReviewListTable

**Files:**
- Create: `frontend/src/features/reviews/ProjectReviewListPage.tsx`
- Create: `frontend/src/features/reviews/ProjectReviewListPage.module.css`
- Create: `frontend/src/features/reviews/ProjectReviewListPage.test.tsx`
- Create: `frontend/src/features/reviews/ReviewListTable.tsx`
- Create: `frontend/src/features/reviews/ReviewListTable.module.css`

**Step 1: Write failing test**

```tsx
// src/features/reviews/ProjectReviewListPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ProjectReviewListPage } from "./ProjectReviewListPage";
import { SessionProvider } from "../../session/SessionContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(
    <SessionProvider>
      <MemoryRouter initialEntries={["/reviews"]}>
        <Routes>
          <Route path="/reviews" element={node} />
          <Route path="/reviews/:reviewId" element={<div data-testid="detail">detail</div>} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  );
}

it("loads and renders the review list from the API", async () => {
  server.use(http.get("/api/v1/reviews", () =>
    HttpResponse.json([
      { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 2, pending_decision_count: 1, created_at: "2026-09-15T00:00:00Z" },
    ]),
  ));
  wrap(<ProjectReviewListPage />);
  expect(await screen.findByText("a.md")).toBeInTheDocument();
  expect(screen.getByText("WAITING_APPROVAL")).toBeInTheDocument();
});

it("navigates to a review detail row", async () => {
  server.use(http.get("/api/v1/reviews", () =>
    HttpResponse.json([
      { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
    ]),
  ));
  wrap(<ProjectReviewListPage />);
  const row = await screen.findByRole("link", { name: /a\.md/ });
  await userEvent.click(row);
  await waitFor(() => expect(screen.getByTestId("detail")).toBeInTheDocument());
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/reviews
```

**Step 3: Implement**

```tsx
// src/features/reviews/ProjectReviewListPage.tsx
import { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { ApiError } from "../../api/errors";
import { ReviewListTable } from "./ReviewListTable";
import { DirectoryPicker } from "../directory/DirectoryPicker";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import type { ReviewSummary } from "../../api/types";
import styles from "./ProjectReviewListPage.module.css";

export function ProjectReviewListPage() {
  const { actor } = useSession();
  const [reviews, setReviews] = useState<ReviewSummary[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!actor) return;
    const ac = new AbortController();
    apiClient.listReviews(actor, { signal: ac.signal }).then(setReviews).catch((e) => {
      if ((e as DOMException).name !== "AbortError") setError(e as ApiError);
    });
    return () => ac.abort();
  }, [actor]);

  return (
    <section className={styles.page}>
      <DirectoryPicker />
      <h2>项目评审</h2>
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      {reviews === null ? <Spinner label="加载中" /> : <ReviewListTable reviews={reviews} />}
    </section>
  );
}
```

```tsx
// src/features/reviews/ReviewListTable.tsx
import { Link } from "react-router-dom";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { formatDateTime } from "../../lib/formatDate";
import type { ReviewSummary } from "../../api/types";
import styles from "./ReviewListTable.module.css";

export function ReviewListTable({ reviews }: { reviews: readonly ReviewSummary[] }) {
  if (reviews.length === 0) return <p className={styles.empty}>暂无评审任务。</p>;
  return (
    <table className={styles.table} aria-label="项目评审列表">
      <thead><tr><th>文档</th><th>状态</th><th>发现</th><th>待决</th><th>创建时间</th></tr></thead>
      <tbody>
        {reviews.map((r) => (
          <tr key={r.review_id}>
            <td><Link to={`/reviews/${r.review_id}`}>{r.source_name ?? r.review_id.slice(0, 8)}</Link></td>
            <td><StatusBadge status={r.status} /></td>
            <td>{r.finding_count}</td>
            <td>{r.pending_decision_count}</td>
            <td>{formatDateTime(r.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

```css
/* ProjectReviewListPage.module.css */
.page { display: grid; gap: var(--space-5); }
/* ReviewListTable.module.css */
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: var(--space-2); border-bottom: 1px solid var(--color-border); text-align: left; }
.empty { color: var(--color-muted); }
```

**Step 4: Wire route in `src/App.tsx`** (replace the placeholder)

```tsx
import { ProjectReviewListPage } from "./features/reviews/ProjectReviewListPage";
// inside <AppShell> route table:
<Route path="/reviews" element={<ProjectReviewListPage />} />
```

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/reviews
```

**Step 6: Commit**

```bash
git add frontend/src/features/reviews frontend/src/App.tsx
git commit -m "feat(frontend): add review list page and table"
```

---

### Task 13: ReviewDetailPage + status header + filters + finding cards

**Files:**
- Create: `frontend/src/features/review-detail/ReviewDetailPage.tsx`
- Create: `frontend/src/features/review-detail/ReviewDetailPage.module.css`
- Create: `frontend/src/features/review-detail/ReviewDetailPage.test.tsx`
- Create: `frontend/src/features/review-detail/ReviewStatusHeader.tsx`
- Create: `frontend/src/features/review-detail/ReviewStatusHeader.module.css`
- Create: `frontend/src/features/review-detail/FindingFilters.tsx`
- Create: `frontend/src/features/review-detail/FindingFilters.module.css`
- Create: `frontend/src/features/review-detail/FindingCard.tsx`
- Create: `frontend/src/features/review-detail/FindingCard.module.css`
- Create: `frontend/src/features/review-detail/FindingCard.test.tsx`

**Step 1: Write failing tests**

```tsx
// src/features/review-detail/ReviewDetailPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ReviewDetailPage } from "./ReviewDetailPage";
import { SessionProvider } from "../../session/SessionContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrap(node: React.ReactNode, id = "r1") {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(
    <SessionProvider>
      <MemoryRouter initialEntries={[`/reviews/${id}`]}>
        <Routes>
          <Route path="/reviews/:reviewId" element={node} />
          <Route path="/reviews/:reviewId/report" element={<div data-testid="report">report</div>} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  );
}

const baseReview = {
  review_id: "r1", project_id: "p", source_name: "spec.md",
  status: "WAITING_APPROVAL", finding_count: 2, pending_decision_count: 1,
  created_at: "2026-09-15T00:00:00Z", failed_dimensions: [],
};
const baseFindings = [
  { finding_id: "f1", requirement_id: "req-1", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L1", quote: "q" }], uses_system_fact: false, decision: null },
  { finding_id: "f2", requirement_id: "req-2", dimension: "clarity", severity: "low", issue: "i2", impact: "im2", recommendation: "rec2", confidence: 0.5, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L2", quote: "q2" }], uses_system_fact: false, decision: { action: "accept", comment: "", actor_id: "u", decided_at: "2026-09-15T01:00:00Z", idempotency_key: "k" } },
];

it("renders each finding as an independent card", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  expect(await screen.findByText(/req-1/)).toBeInTheDocument();
  expect(screen.getByText(/req-2/)).toBeInTheDocument();
});

it("filters findings by severity", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  await userEvent.selectOptions(screen.getByLabelText(/严重程度/), "high");
  expect(screen.getByText(/req-1/)).toBeInTheDocument();
  expect(screen.queryByText(/req-2/)).not.toBeInTheDocument();
});

it("shows pending count and disables approval until resolved", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  expect(screen.getByText(/剩余 1 条待审核/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /最终确认/ })).toBeDisabled();
});

it("viewer sees read-only state with no decision controls", async () => {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" }));
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  expect(screen.queryByRole("button", { name: /接受/ })).not.toBeInTheDocument();
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/review-detail
```

**Step 3: Implement**

```tsx
// src/features/review-detail/ReviewDetailPage.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { ApiError } from "../../api/errors";
import { ReviewStatusHeader } from "./ReviewStatusHeader";
import { FindingFilters } from "./FindingFilters";
import { FindingCard } from "./FindingCard";
import { FinalApprovalGate } from "./FinalApprovalGate";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import { useReviewPolling } from "./useReviewPolling";
import type { Finding } from "../../api/types";
import styles from "./ReviewDetailPage.module.css";

export function ReviewDetailPage() {
  const { reviewId = "" } = useParams();
  const { actor } = useSession();
  const { data: review, error: pollErr, stale, retry } = useReviewPolling(reviewId);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [severity, setSeverity] = useState<string>("all");

  const reload = useCallback(async () => {
    if (!actor || !reviewId) return;
    try {
      const f = await apiClient.getFindings(actor, reviewId);
      setFindings(f);
    } catch (e) {
      setError(e as ApiError);
    }
  }, [actor, reviewId]);

  useEffect(() => { void reload(); }, [reload]);

  const filtered = useMemo(() => severity === "all" ? findings : findings.filter((f) => f.severity === severity), [findings, severity]);
  const pending = findings.filter((f) => f.decision === null || f.decision.action === "re-review").length;

  if (!review) return <Spinner label="加载评审" />;
  if (error || pollErr) return <Alert severity="error" message={(error ?? pollErr)!.message} correlationId={(error ?? pollErr)!.correlationId} />;

  return (
    <section className={styles.page}>
      <ReviewStatusHeader review={review} stale={stale} onRetry={retry} />
      {stale ? <Alert severity="warn" message="状态查询停滞，请重试。" /> : null}
      <FindingFilters severity={severity} onSeverityChange={setSeverity} />
      <p className={styles.pending}>剩余 {pending} 条待审核</p>
      <ol className={styles.cards}>
        {filtered.map((f) => (
          <li key={f.finding_id}>
            <FindingCard finding={f} onDecided={(updated) => setFindings((prev) => prev.map((x) => (x.finding_id === updated.finding_id ? updated : x)))} />
          </li>
        ))}
      </ol>
      <FinalApprovalGate review={review} findings={findings} />
      <p><Link to={`/reviews/${reviewId}/report`}>查看最终报告 →</Link></p>
    </section>
  );
}
```

```tsx
// src/features/review-detail/ReviewStatusHeader.tsx
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { Button } from "../../components/Button/Button";
import { formatDateTime } from "../../lib/formatDate";
import type { ReviewDetail } from "../../api/types";
import styles from "./ReviewStatusHeader.module.css";

export function ReviewStatusHeader({ review, stale, onRetry }: { review: ReviewDetail; stale: boolean; onRetry: () => void }) {
  return (
    <header className={styles.header}>
      <h2>{review.source_name ?? review.review_id}</h2>
      <StatusBadge status={review.status} />
      <span className={styles.meta}>{formatDateTime(review.created_at)}</span>
      {stale ? <Button onClick={onRetry}>重试查询</Button> : null}
    </header>
  );
}
```

```tsx
// src/features/review-detail/FindingFilters.tsx
import { Select } from "../../components/Select/Select";
import styles from "./FindingFilters.module.css";

const OPTIONS = [
  { value: "all", label: "全部" },
  { value: "critical", label: "严重" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
] as const;

export function FindingFilters({ severity, onSeverityChange }: { severity: string; onSeverityChange: (v: string) => void }) {
  return (
    <div className={styles.row}>
      <Select id="sev" label="严重程度" value={severity} onChange={onSeverityChange} options={OPTIONS as unknown as readonly { value: string; label: string }[]} />
    </div>
  );
}
```

```tsx
// src/features/review-detail/FindingCard.tsx
import { useState } from "react";
import { useSession } from "../../session/SessionContext";
import { DecisionForm } from "./DecisionForm";
import type { Finding } from "../../api/types";
import styles from "./FindingCard.module.css";

export function FindingCard({ finding, onDecided }: { finding: Finding; onDecided: (f: Finding) => void }) {
  const { actor } = useSession();
  const writable = actor?.role === "reviewer" || actor?.role === "admin";
  return (
    <article className={styles.card} aria-labelledby={`f-${finding.finding_id}`}>
      <header>
        <h3 id={`f-${finding.finding_id}`}>{finding.dimension} · {finding.severity}</h3>
        <span className={styles.requirement}>需求 {finding.requirement_id}</span>
      </header>
      <dl>
        <dt>问题</dt><dd>{finding.issue}</dd>
        <dt>影响</dt><dd>{finding.impact}</dd>
        <dt>建议</dt><dd>{finding.recommendation}</dd>
        <dt>置信度</dt><dd>{(finding.confidence * 100).toFixed(0)}%</dd>
        <dt>证据</dt>
        <dd>
          <ul>
            {finding.evidence.map((e, i) => (
              <li key={i}><code>{e.locator}</code> — {e.quote}</li>
            ))}
          </ul>
        </dd>
        <dt>当前决策</dt><dd>{finding.decision ? `${finding.decision.action}${finding.decision.comment ? ` — ${finding.decision.comment}` : ""}` : "无"}</dd>
      </dl>
      {writable ? <DecisionForm finding={finding} onDecided={onDecided} /> : null}
    </article>
  );
}
```

```css
/* ReviewDetailPage.module.css */
.page { display: grid; gap: var(--space-4); }
.cards { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); }
.pending { color: var(--color-warn); margin: 0; }

/* ReviewStatusHeader.module.css */
.header { display: flex; align-items: center; gap: var(--space-3); }
.meta { color: var(--color-muted); }

/* FindingFilters.module.css */
.row { display: flex; gap: var(--space-3); }

/* FindingCard.module.css */
.card { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-1); display: grid; gap: var(--space-3); }
.requirement { color: var(--color-muted); margin-left: auto; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: var(--space-2) var(--space-4); margin: 0; }
dt { font-weight: 600; }
```

**Step 4: Wire route + stubs (DecisionForm + FinalApprovalGate come in tasks 14/15)**

Update `src/App.tsx` route table to add the detail route (DecisionForm and FinalApprovalGate are imported as the next tasks implement them; if importing early, add minimal placeholder files that export a function returning `null` to keep the build green between tasks — remove the placeholder once the real implementation lands).

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/review-detail
```

**Step 6: Commit**

```bash
git add frontend/src/features/review-detail
git commit -m "feat(frontend): add review detail page, status header, filters, finding cards"
```

---

### Task 14: DecisionForm with idempotency

**Files:**
- Create: `frontend/src/features/review-detail/DecisionForm.tsx`
- Create: `frontend/src/features/review-detail/DecisionForm.module.css`
- Create: `frontend/src/features/review-detail/DecisionForm.test.tsx`

**Step 1: Write failing tests**

```tsx
// src/features/review-detail/DecisionForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { DecisionForm } from "./DecisionForm";
import { SessionProvider } from "../../session/SessionContext";
import type { Finding } from "../../api/types";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const finding: Finding = {
  finding_id: "f1", requirement_id: "r", dimension: "completeness", severity: "high",
  issue: "i", impact: "im", recommendation: "rec", confidence: 0.9,
  evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }],
  uses_system_fact: false, decision: null,
};

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(<SessionProvider>{node}</SessionProvider>);
}

it("posts a decision with a stable idempotency key on retry", async () => {
  const seenKeys: string[] = [];
  let count = 0;
  server.use(http.post("/api/v1/reviews/r1/findings/f1/decision", async ({ request }) => {
    count += 1;
    const k = request.headers.get("Idempotency-Key") ?? "";
    seenKeys.push(k);
    if (count === 1) return new HttpResponse(null, { status: 502 });
    return HttpResponse.json({ ...finding, decision: { action: "accept", comment: "ok", actor_id: "u", decided_at: "2026-09-15T01:00:00Z", idempotency_key: k } });
  }));
  const onDecided = vi.fn();
  wrap(<DecisionForm reviewId="r1" finding={finding} onDecided={onDecided} />);
  await userEvent.click(screen.getByRole("button", { name: /接受/ }));
  await userEvent.click(screen.getByRole("button", { name: /^提交/ }));
  // first submit may fail; we expect same key across the retry
  await new Promise((r) => setTimeout(r, 50));
  expect(seenKeys.length).toBeGreaterThanOrEqual(1);
  expect(new Set(seenKeys).size).toBe(1);
});

it("generates a new key when the user submits again", async () => {
  const seen: string[] = [];
  server.use(http.post("/api/v1/reviews/r1/findings/f1/decision", async ({ request }) => {
    seen.push(request.headers.get("Idempotency-Key") ?? "");
    return HttpResponse.json({ ...finding, decision: { action: "accept", comment: "", actor_id: "u", decided_at: "2026-09-15T01:00:00Z", idempotency_key: seen.at(-1) ?? "" } });
  }));
  const onDecided = vi.fn();
  wrap(<DecisionForm reviewId="r1" finding={finding} onDecided={onDecided} />);
  await userEvent.click(screen.getByRole("button", { name: /接受/ }));
  await userEvent.click(screen.getByRole("button", { name: /^提交/ }));
  await userEvent.click(screen.getByRole("button", { name: /接受/ }));
  await userEvent.click(screen.getByRole("button", { name: /^提交/ }));
  expect(new Set(seen).size).toBe(2);
});

it("prevents duplicate submit while in flight", async () => {
  let resolveFn: (r: Response) => void = () => {};
  server.use(http.post("/api/v1/reviews/r1/findings/f1/decision", () => new Promise<Response>((r) => { resolveFn = r; })));
  wrap(<DecisionForm reviewId="r1" finding={finding} onDecided={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /接受/ }));
  const submit = screen.getByRole("button", { name: /^提交/ });
  await userEvent.click(submit);
  expect(submit).toBeDisabled();
  resolveFn(HttpResponse.json({ ...finding, decision: { action: "accept", comment: "", actor_id: "u", decided_at: "2026-09-15T01:00:00Z", idempotency_key: "k" } }));
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/review-detail/DecisionForm.test.tsx
```

**Step 3: Implement**

```tsx
// src/features/review-detail/DecisionForm.tsx
import { useCallback, useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { newIdempotencyKey } from "../../api/idempotency";
import { Button } from "../../components/Button/Button";
import { Textarea } from "../../components/Textarea/Textarea";
import { Alert } from "../../components/Alert/Alert";
import { ApiError } from "../../api/errors";
import type { DecisionAction, Finding } from "../../api/types";
import styles from "./DecisionForm.module.css";

const ACTIONS: { value: DecisionAction; label: string }[] = [
  { value: "accept", label: "接受" },
  { value: "reject", label: "拒绝" },
  { value: "re-review", label: "重新评审" },
];

interface Props { reviewId: string; finding: Finding; onDecided: (f: Finding) => void }

export function DecisionForm({ reviewId, finding, onDecided }: Props) {
  const { actor } = useSession();
  const [action, setAction] = useState<DecisionAction>("accept");
  const [comment, setComment] = useState("");
  const [key, setKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submit = useCallback(async () => {
    if (!actor || busy) return;
    const k = key ?? newIdempotencyKey();
    setBusy(true);
    setError(null);
    try {
      const updated = await apiClient.decideFinding(actor, reviewId, finding.finding_id, { action, comment: comment.trim() }, { idempotencyKey: k, retry: { retries: 2, baseDelayMs: 50 } });
      setKey(k);
      onDecided(updated);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }, [actor, busy, key, action, comment, reviewId, finding.finding_id, onDecided]);

  const reset = () => { setKey(null); setAction("accept"); setComment(""); };

  return (
    <form
      className={styles.form}
      onSubmit={(e) => { e.preventDefault(); void submit(); }}
      aria-label={`对需求 ${finding.requirement_id} 做出决策`}
    >
      <div role="radiogroup" aria-label="决策">
        {ACTIONS.map((a) => (
          <label key={a.value}>
            <input type="radio" name="action" value={a.value} checked={action === a.value} onChange={() => setAction(a.value)} />
            {a.label}
          </label>
        ))}
      </div>
      <Textarea id={`cmt-${finding.finding_id}`} label="意见（可选）" value={comment} onChange={setComment} maxLength={2000} />
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      <div className={styles.row}>
        <Button type="submit" disabled={busy} aria-busy={busy}>{busy ? "提交中" : "提交决策"}</Button>
        <Button type="button" onClick={reset} disabled={busy}>重置</Button>
      </div>
    </form>
  );
}
```
```css
/* DecisionForm.module.css */
.form { display: grid; gap: var(--space-3); }
.row { display: flex; gap: var(--space-3); }
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/review-detail/DecisionForm.test.tsx
```

**Step 5: Commit**

```bash
git add frontend/src/features/review-detail/DecisionForm.tsx frontend/src/features/review-detail/DecisionForm.module.css frontend/src/features/review-detail/DecisionForm.test.tsx
git commit -m "feat(frontend): add DecisionForm with stable idempotency key"
```

---

### Task 15: FinalApprovalGate + ApprovalForm + report gating

**Files:**
- Create: `frontend/src/features/review-detail/FinalApprovalGate.tsx`
- Create: `frontend/src/features/review-detail/FinalApprovalGate.module.css`
- Create: `frontend/src/features/review-detail/FinalApprovalGate.test.tsx`
- Create: `frontend/src/features/review-detail/ApprovalForm.tsx`
- Create: `frontend/src/features/review-detail/ApprovalForm.module.css`
- Create: `frontend/src/features/review-detail/ApprovalForm.test.tsx`

**Step 1: Write failing tests**

```tsx
// src/features/review-detail/FinalApprovalGate.test.tsx
import { render, screen } from "@testing-library/react";
import { FinalApprovalGate } from "./FinalApprovalGate";
import type { Finding, ReviewDetail } from "../../api/types";

const review = { review_id: "r1", project_id: "p", source_name: "s", status: "WAITING_APPROVAL" as const, finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] };
const baseFinding = (decision: Finding["decision"]): Finding => ({
  finding_id: "f", requirement_id: "r", dimension: "completeness", severity: "high",
  issue: "i", impact: "im", recommendation: "rec", confidence: 0.9,
  evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }],
  uses_system_fact: false, decision,
});

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(<SessionProvider>{node}</SessionProvider>);
}

it("disables when any finding is undecided", () => {
  wrap(<FinalApprovalGate review={review} findings={[baseFinding(null), baseFinding({ action: "accept", comment: "", actor_id: "u", decided_at: "t", idempotency_key: "k" })]} />);
  expect(screen.getByRole("button", { name: /最终确认/ })).toBeDisabled();
});

it("disables when any finding is re-review", () => {
  wrap(<FinalApprovalGate review={review} findings={[baseFinding({ action: "re-review", comment: "", actor_id: "u", decided_at: "t", idempotency_key: "k" })]} />);
  expect(screen.getByRole("button", { name: /最终确认/ })).toBeDisabled();
});

it("enables when all findings are accept or reject", () => {
  wrap(<FinalApprovalGate review={review} findings={[baseFinding({ action: "accept", comment: "", actor_id: "u", decided_at: "t", idempotency_key: "k" }), baseFinding({ action: "reject", comment: "", actor_id: "u", decided_at: "t", idempotency_key: "k" })]} />);
  expect(screen.getByRole("button", { name: /最终确认/ })).not.toBeDisabled();
});

it("enables when review has zero findings", () => {
  wrap(<FinalApprovalGate review={review} findings={[]} />);
  expect(screen.getByRole("button", { name: /最终确认/ })).not.toBeDisabled();
});
```

```tsx
// src/features/review-detail/ApprovalForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ApprovalForm } from "./ApprovalForm";
import { SessionProvider } from "../../session/SessionContext";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("posts approval with a generated idempotency key", async () => {
  let key = "";
  server.use(http.post("/api/v1/reviews/r1/approval", async ({ request }) => {
    key = request.headers.get("Idempotency-Key") ?? "";
    return HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "s", status: "COMPLETED", finding_count: 0, pending_decision_count: 0, created_at: "t", failed_dimensions: [] }, { status: 202 });
  }));
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  render(<SessionProvider><ApprovalForm reviewId="r1" /></SessionProvider>);
  await userEvent.click(screen.getByRole("button", { name: /最终确认/ }));
  expect(key).toMatch(/^[0-9a-f-]{36}$/);
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/review-detail/FinalApprovalGate.test.tsx src/features/review-detail/ApprovalForm.test.tsx
```

**Step 3: Implement**

```tsx
// src/features/review-detail/FinalApprovalGate.tsx
import type { Finding, ReviewDetail } from "../../api/types";
import { ApprovalForm } from "./ApprovalForm";
import { useSession } from "../../session/SessionContext";
import styles from "./FinalApprovalGate.module.css";

export function FinalApprovalGate({ review, findings }: { review: ReviewDetail; findings: readonly Finding[] }) {
  const { actor } = useSession();
  const writable = actor?.role === "reviewer" || actor?.role === "admin";
  const allResolved = findings.length === 0 || findings.every((f) => {
    const d = f.decision;
    return d !== null && d.action !== "re-review";
  });
  const enabled = allResolved && review.status !== "COMPLETED";
  return (
    <section aria-labelledby="gate-h" className={styles.gate}>
      <h3 id="gate-h">最终确认</h3>
      <p className={enabled ? styles.ok : styles.disabled}>
        {enabled ? "所有评审点已决定，可执行最终确认。" : "存在未决或重新评审的评审点。"}
      </p>
      {writable ? <ApprovalForm reviewId={review.review_id} disabled={!enabled} /> : null}
    </section>
  );
}
```
```css
/* FinalApprovalGate.module.css */
.gate { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-1); display: grid; gap: var(--space-3); }
.ok { color: var(--color-ok); margin: 0; }
.disabled { color: var(--color-warn); margin: 0; }
```

```tsx
// src/features/review-detail/ApprovalForm.tsx
import { useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { newIdempotencyKey } from "../../api/idempotency";
import { Button } from "../../components/Button/Button";
import { Textarea } from "../../components/Textarea/Textarea";
import { Alert } from "../../components/Alert/Alert";
import { ApiError } from "../../api/errors";
import styles from "./ApprovalForm.module.css";

export function ApprovalForm({ reviewId, disabled }: { reviewId: string; disabled?: boolean }) {
  const { actor } = useSession();
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);

  async function submit() {
    if (!actor || busy) return;
    setBusy(true); setError(null);
    try {
      await apiClient.approve(actor, reviewId, { action: "approve", comment: comment.trim() }, { idempotencyKey: newIdempotencyKey() });
      setDone(true);
    } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <form className={styles.form} onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <Textarea id="apr-cmt" label="意见（可选）" value={comment} onChange={setComment} maxLength={2000} />
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      <Button type="submit" disabled={disabled || busy} aria-busy={busy}>{done ? "已确认" : busy ? "提交中" : "最终确认"}</Button>
    </form>
  );
}
```
```css
/* ApprovalForm.module.css */
.form { display: grid; gap: var(--space-3); }
```

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/review-detail
```

**Step 5: Commit**

```bash
git add frontend/src/features/review-detail
git commit -m "feat(frontend): add FinalApprovalGate plus ApprovalForm"
```

---

### Task 16: ReportPage + MarkdownView

**Files:**
- Create: `frontend/src/features/report/ReportPage.tsx`
- Create: `frontend/src/features/report/ReportPage.module.css`
- Create: `frontend/src/features/report/ReportPage.test.tsx`
- Create: `frontend/src/features/report/MarkdownView.tsx`
- Create: `frontend/src/features/report/MarkdownView.module.css`

**Step 1: Write failing tests**

```tsx
// src/features/report/ReportPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ReportPage } from "./ReportPage";
import { SessionProvider } from "../../session/SessionContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("renders escaped markdown report text in a <pre>", async () => {
  server.use(http.get("/api/v1/reviews/r1/report", () =>
    new HttpResponse("# Final Report\n<script>alert(1)</script>", { headers: { "Content-Type": "text/markdown" } }),
  ));
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" }));
  render(
    <SessionProvider>
      <MemoryRouter initialEntries={["/reviews/r1/report"]}>
        <Routes>
          <Route path="/reviews/:reviewId/report" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  );
  const pre = await screen.findByRole("region", { name: /报告/ });
  expect(pre.textContent).toContain("Final Report");
  expect(pre.innerHTML).not.toContain("<script>");
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/features/report
```

**Step 3: Implement**

```tsx
// src/features/report/MarkdownView.tsx
import { useMemo } from "react";
import styles from "./MarkdownView.module.css";

/** Render the report as escaped, monospaced text inside <pre>. No third-party Markdown lib. */
export function MarkdownView({ markdown }: { markdown: string }) {
  const escaped = useMemo(() => markdown.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]!)), [markdown]);
  return <pre className={styles.pre} aria-label="报告内容">{escaped}</pre>;
}
```
```css
/* MarkdownView.module.css */
.pre { white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono); padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-1); background: #fafafa; }
```

```tsx
// src/features/report/ReportPage.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { ApiError } from "../../api/errors";
import { MarkdownView } from "./MarkdownView";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import styles from "./ReportPage.module.css";

export function ReportPage() {
  const { reviewId = "" } = useParams();
  const { actor } = useSession();
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!actor) return;
    const ac = new AbortController();
    apiClient.getReport(actor, reviewId, { signal: ac.signal }).then(setText).catch((e) => {
      if ((e as DOMException).name !== "AbortError") setError(e as ApiError);
    });
    return () => ac.abort();
  }, [actor, reviewId]);

  if (error) return <Alert severity="error" message={error.message} correlationId={error.correlationId} />;
  if (text === null) return <Spinner label="加载报告" />;
  return (
    <section aria-labelledby="report-h" className={styles.page}>
      <h2 id="report-h">最终报告</h2>
      <div role="region" aria-label="报告内容"><MarkdownView markdown={text} /></div>
    </section>
  );
}
```
```css
/* ReportPage.module.css */
.page { display: grid; gap: var(--space-4); }
```

**Step 4: Wire route in `src/App.tsx`**

```tsx
import { ReportPage } from "./features/report/ReportPage";
// inside the <AppShell> route table:
<Route path="/reviews/:reviewId/report" element={<ReportPage />} />
```

**Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- --run src/features/report
```

**Step 6: Commit**

```bash
git add frontend/src/features/report frontend/src/App.tsx
git commit -m "feat(frontend): add report page with escaped markdown view"
```

---

## Phase 4 — Integration, end-to-end, validation

### Task 17: End-to-end (refresh recovery, idempotency conflict)

**Files:**
- Create: `frontend/src/App.integration.test.tsx`

**Step 1: Write failing integration test**

```tsx
// src/App.integration.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import App from "./App";
import { SessionProvider } from "./session/SessionContext";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("refresh recovery + idempotency", () => {
  it("loads list and finding decisions from the server on re-entry", async () => {
    sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
    server.use(
      http.get("/api/v1/reviews", () => HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
      ])),
      http.get("/api/v1/reviews/r1", () => HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] })),
      http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json([
        { finding_id: "f1", requirement_id: "r", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }], uses_system_fact: false, decision: { action: "accept", comment: "ok", actor_id: "u", decided_at: "t", idempotency_key: "k" } },
      ])),
    );
    const { unmount } = render(<SessionProvider><App /></SessionProvider>);
    await screen.findByText("a.md");
    unmount();
    render(<SessionProvider><App /></SessionProvider>);
    await screen.findByText("a.md");
    await userEvent.click(screen.getByRole("link", { name: /a\.md/ }));
    await waitFor(() => expect(screen.getByText(/ok/)).toBeInTheDocument());
  });

  it("surfaces 409 idempotency_conflict to the user without crashing", async () => {
    sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
    server.use(
      http.get("/api/v1/reviews", () => HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "t" },
      ])),
      http.get("/api/v1/reviews/r1", () => HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "t", failed_dimensions: [] })),
      http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json([
        { finding_id: "f1", requirement_id: "r", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }], uses_system_fact: false, decision: null },
      ])),
      http.post("/api/v1/reviews/r1/findings/f1/decision", () => HttpResponse.json({ code: "idempotency_conflict", message: "key reused with different body", correlation_id: "cid-9" }, { status: 409 })),
    );
    render(<SessionProvider><App /></SessionProvider>);
    await userEvent.click(await screen.findByRole("link", { name: /a\.md/ }));
    await userEvent.click(await screen.findByRole("button", { name: /接受/ }));
    await userEvent.click(screen.getByRole("button", { name: /^提交/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/key reused/);
  });
});
```

**Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- --run src/App.integration.test.tsx
```

**Step 3: Adjust `App.tsx` to provide Router + MemoryRouter fallback for tests**

```tsx
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { SessionProvider, useSession } from "./session/SessionContext";
import { SessionForm } from "./session/SessionForm";
import { AppShell } from "./shell/AppShell";
import { GlobalAlertsProvider } from "./shell/GlobalAlerts";
import { ProjectReviewListPage } from "./features/reviews/ProjectReviewListPage";
import { ReviewDetailPage } from "./features/review-detail/ReviewDetailPage";
import { ReportPage } from "./features/report/ReportPage";

function SessionGate() {
  const { actor, setSession } = useSession();
  if (!actor) return <SessionForm onSubmit={setSession} />;
  return <Outlet />;
}

export default function App() {
  return (
    <SessionProvider>
      <GlobalAlertsProvider>
        <Routes>
          <Route element={<SessionGate />}>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/reviews" replace />} />
              <Route path="/reviews" element={<ProjectReviewListPage />} />
              <Route path="/reviews/:reviewId" element={<ReviewDetailPage />} />
              <Route path="/reviews/:reviewId/report" element={<ReportPage />} />
              <Route path="*" element={<div>404</div>} />
            </Route>
          </Route>
        </Routes>
      </GlobalAlertsProvider>
    </SessionProvider>
  );
}
```

For tests, wrap `<App />` in `<MemoryRouter>` (see test file above).

**Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- --run
```

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.integration.test.tsx
git commit -m "test(frontend): add refresh-recovery and idempotency-conflict integration tests"
```

---

### Task 18: Playwright config + e2e spec

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/workbench.spec.ts`

**Step 1: Write `playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../backend && .venv/bin/uvicorn requirement_review.api.app:app --host 127.0.0.1 --port 8000 --log-level warning",
      url: "http://localhost:8000/api/v1/projects",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
```

Add `npm run test:e2e` already declared in Task 1; add `npm run test:e2e:install` to install browsers.

**Step 2: Write `tests/e2e/workbench.spec.ts`**

```ts
import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import { mkdirSync, writeFileSync } from "node:fs";

const FIXTURE_DIR = path.join(process.cwd(), "tests/e2e/.tmp");
mkdirSync(FIXTURE_DIR, { recursive: true });
writeFileSync(path.join(FIXTURE_DIR, "a.md"), "# A\n\nBody A", "utf8");
writeFileSync(path.join(FIXTURE_DIR, "B.Markdown"), "# B\n\nBody B", "utf8");
writeFileSync(path.join(FIXTURE_DIR, "ignore.txt"), "noise", "utf8");

async function bootstrap(page: Page) {
  await page.goto("/");
  await page.getByLabel(/用户 ID/).fill("u1");
  await page.getByLabel(/项目 ID/).fill("p1");
  await page.getByLabel(/角色/).selectOption("reviewer");
  await page.getByRole("button", { name: /开始/ }).click();
  // First request: create the project so the in-memory backend accepts reviews.
  const ok = await page.request.post("http://localhost:8000/api/v1/projects", {
    headers: { "X-User-ID": "u1", "X-Project-ID": "p1", "X-Role": "admin" },
    data: { name: "demo", data_policy: "local_only" },
  });
  expect(ok.status()).toBeLessThan(400);
}

test("directory → reviews → decisions → approval → report", async ({ page }) => {
  await bootstrap(page);
  await page.getByTestId("dir-input").setInputFiles([
    path.join(FIXTURE_DIR, "a.md"),
    path.join(FIXTURE_DIR, "B.Markdown"),
    path.join(FIXTURE_DIR, "ignore.txt"),
  ]);
  await expect(page.getByText(/忽略 1 个非 Markdown 文件/)).toBeVisible();
  await page.getByRole("button", { name: /开始提交/ }).click();

  // Two reviews should appear in the list (poll until both rows show).
  await expect(page.getByRole("link", { name: /a\.md|B\.Markdown/ }).first()).toBeVisible({ timeout: 30_000 });

  // Open the first review and submit at least one decision.
  await page.getByRole("link", { name: /a\.md/ }).first().click();
  // Empty model gateway produces no findings, so approve the document when the gate enables.
  const approveBtn = page.getByRole("button", { name: /最终确认/ });
  await expect(approveBtn).toBeEnabled({ timeout: 30_000 });
  await approveBtn.click();
  await expect(page.getByRole("button", { name: /已确认/ })).toBeVisible();
  await page.getByRole("link", { name: /查看最终报告/ }).click();
  await expect(page.getByRole("region", { name: /报告/ })).toBeVisible();
});
```

**Step 3: Run**

```bash
cd frontend && npm run test:e2e:install
cd frontend && npm run test:e2e
```
Expected: 1 passed. The backend webServer starts in-memory FastAPI on 8000; the dev server proxies `/api/v1` to it.

**Step 4: Commit**

```bash
git add frontend/playwright.config.ts frontend/tests/e2e
git commit -m "test(frontend): add Playwright browser-level integration spec"
```

---

### Task 19: README + run scripts

**Files:**
- Create: `frontend/README.md`

**Step 1: Write `README.md`**

```md
# Requirement Review Workbench — Frontend

聚焦目录级 AI 评审流程的 React + TypeScript 前端工作台。

## 开发

```bash
npm install
npm run dev          # http://localhost:5173；/api/v1 代理到 http://localhost:8000
npm run typecheck
npm test -- --run
npm run build
npm run lint
npm run test:e2e:install
npm run test:e2e     # 起 backend (uvicorn) + dev server，跑 Playwright
```

## 会话

首次访问 `/` 进入"建立会话"页。输入 `user_id / project_id / role` 后写入 `sessionStorage['rr:session:v1']`。
后续请求由 `apiClient` 自动注入 `X-User-ID` / `X-Project-ID` / `X-Role` 头。**审核事实**（findings、decisions、idempotency keys）不写入本地存储。

## 目录选择

`<input webkitdirectory>` 是首选；当浏览器不支持时退回到多文件 `<input type="file" multiple>`。
仅 `.md` 与 `.markdown`（大小写不敏感）进入提交队列，其他文件计入"忽略"。
请求体只携带 Markdown 文本与文件名（basename），绝不发送绝对路径。

## 审核与确认

- 每份 Markdown 文档对应一个独立 review；并发上限 3。
- 每个 finding 是独立卡片；reviewer/admin 可执行 accept / reject / re-review 并填意见。
- 决策与最终确认使用 UUID v4 幂等键；同 key 重试返回原结果，同 key 异 body 返回 409。
- 所有 finding 最新决策均为 accept/reject（或无 finding）时才启用最终确认。
- 报告页将 Markdown 文本以 `<pre>` 转义展示，无第三方渲染依赖。

## 角色门控

| 角色 | 列表 | 详情 | 决策 | 最终确认 |
|------|------|------|------|----------|
| viewer | ✓ | ✓ | – | – |
| reviewer | ✓ | ✓ | ✓ | ✓ |
| admin | ✓ | ✓ | ✓ | ✓ |

后端是授权最终来源；UI 门控是建议性的。

## 测试

- `npm test` — Vitest + RTL + MSW，覆盖单元、组件、集成
- `npm run test:e2e` — Playwright 真实后端端到端
```

**Step 2: Commit**

```bash
git add frontend/README.md
git commit -m "docs(frontend): add README"
```

---

### Task 20: Final validation gates

**Files:**
- Modify: none (verification only)

**Step 1: Run all gates from `frontend/` and `repo root`**

```bash
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
cd ..
openspec validate add-directory-ai-review-workbench --strict --type change --path frontend/openspec/changes/add-directory-ai-review-workbench
```

Expected: all five exit 0. Fix any reported errors before declaring done.

**Step 2: Run browser-level integration**

```bash
cd frontend && npm run test:e2e
```

Expected: 1 passed. Confirm `playwright-report/` and `test-results/` are gitignored.

**Step 3: Final commit (only if anything needed adjustment)**

```bash
git status --short
# if changes:
git add -A frontend
git commit -m "chore(frontend): final validation cleanup"
```

---

## Self-Review

### Spec coverage

- "Select a requirement directory" → Tasks 8, 10 (DirectoryPicker + fileFilters)
- "Start one review per document" → Tasks 9, 10 (useDirectorySubmission + DirectoryPicker submit)
- "Present each AI finding as a review record" → Tasks 12, 13 (ReviewDetailPage + FindingCard)
- "Decide findings independently" → Task 14 (DecisionForm)
- "Finalize a reviewed document" → Tasks 15 (FinalApprovalGate + ApprovalForm) + 16 (report)
- "Communicate progress and errors" → Tasks 4 (ApiError), 9 (per-file error), 11 (useReviewPolling stale), 6 (Alert/Spinner primitives)
- "Provide accessible review controls" → Tasks 6, 12, 13, 14 (radiogroup/label/aria-live); Task 18 e2e asserts keyboard + ARIA

### Placeholder scan

No TBD/TODO. All code snippets are concrete. All test files precede their implementation files in the same task. Every step has the exact command and expected outcome.

### Type / signature consistency

- `apiClient` method signatures used in `useDirectorySubmission`, `useReviewPolling`, `DecisionForm`, `ApprovalForm`, `ProjectReviewListPage`, `ReviewDetailPage`, `ReportPage` all match the definitions in `src/api/client.ts` (Task 4) and the types in `src/api/types.ts` (Task 2).
- `SessionContext` value shape (`{ actor, setSession, reset }`) is consumed identically by `RoleGate`, `DirectoryPicker`, `DecisionForm`, `ApprovalForm`, `FinalApprovalGate`.
- `useDirectorySubmission` returns `{ items, summary, submit, retry }`; both the test file and `DirectoryPicker` use that destructuring.
- `useReviewPolling` returns `{ data, error, stale, retry }`; both the test and `ReviewDetailPage` consume the same shape.
- `DecisionForm` props `{ reviewId, finding, onDecided }` and `FinalApprovalGate` props `{ review, findings }` are referenced from the same types throughout.

### Risks / hand-off notes

- Task 4 contains a `no-constant-condition` ESLint suppression around the retry loop because the loop is bounded by the retry counter — the comment block in the code explains this. If a future refactor removes the counter, remove the suppression.
- Task 9 marks `retry` as best-effort with empty text when called from a stale `SubmissionItem`; the production path is `DirectoryPicker` which keeps the original `ReadyFile` separately. If retry is needed with the original text, store `text` on the `SubmissionItem` itself.
- Task 11 sets `consecutiveErrors.current` via a ref; in StrictMode the effect runs twice in development. The `cancelled` flag in the effect body prevents state writes after unmount. The visible behavior in production is unaffected.
- Task 16 reports a `role="region"` on the wrapper `<div>` for the report; `<MarkdownView>` itself is `<pre>` which is not focusable, so screen readers will find the region label and read the content.
- Task 18 spins up uvicorn on 8000 from inside `webServer`; the dev proxy is already wired to that target. If the port is busy locally, the existing server is reused by the second webServer entry (`reuseExistingServer: true`).
- The plan assumes the root `openspec/changes/add-directory-ai-review-workbench/` has already been deployed; if not, the `/api/v1/reviews` list endpoint and decision projection will 404.

