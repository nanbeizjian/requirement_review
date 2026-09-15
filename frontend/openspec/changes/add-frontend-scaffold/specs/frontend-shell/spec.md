## Purpose

Define the frontend component shell: session context, typed HTTP client, error surfacing, accessibility, idempotency-key generation, and routing for the requirement review user journeys. This spec consumes the root public contracts and does not redefine them.

## ADDED Requirements

### Requirement: Session context

The frontend SHALL maintain a single session context storing `userId`, `projectId`, and `role` (`admin`, `reviewer`, or `viewer`). The session SHALL be the only source of identity for outgoing requests. The session SHALL be persisted to `localStorage` under a versioned key and SHALL be restorable on page load.

#### Scenario: Active session sends correct headers

- **WHEN** any HTTP request is sent while a session is active
- **THEN** the request includes `X-User-ID`, `X-Project-ID`, and `X-Role` headers matching the active session values

#### Scenario: Missing session blocks protected requests

- **WHEN** the user attempts a request without an active session
- **THEN** the UI surfaces a clear prompt to set the session and does not send the request

#### Scenario: Session restored on reload

- **WHEN** the page reloads and a valid session is present in `localStorage`
- **THEN** the session is restored without prompting the user

### Requirement: Typed HTTP client

The frontend SHALL expose a typed `RequirementReviewClient` whose public methods map one-to-one to backend endpoints in `openspec/specs/public-contracts/spec.md`. Field names SHALL mirror backend Pydantic models. Every method SHALL require a `Session` argument.

#### Scenario: All public requests carry identity headers

- **WHEN** any client method is called
- **THEN** the outgoing request includes `X-User-ID`, `X-Project-ID`, and `X-Role`

#### Scenario: Approval and finding decisions send idempotency keys

- **WHEN** `approveReview` or `decideFinding` is called
- **THEN** the request includes an `Idempotency-Key` header generated for that user action

#### Scenario: Non-Markdown uploads are rejected client-side

- **WHEN** `uploadKnowledge` receives a file whose name does not end with `.md` or `.markdown`
- **THEN** the client rejects the request with an `ApiError` whose `status` is `415` without contacting the backend

### Requirement: Compatible errors

The frontend SHALL decode every non-2xx response into an `ApiError` carrying the stable `{ code, message, correlation_id }` shape from `openspec/specs/public-contracts/spec.md`. Stack traces, secrets, and internal diagnostics SHALL NOT be exposed in the UI.

#### Scenario: Backend returns stable error shape

- **WHEN** the backend responds with a non-2xx status and a JSON body matching the stable error contract
- **THEN** the UI displays the `message` and the `correlation_id` from the body
- **AND** no stack trace or raw response body is rendered

#### Scenario: Backend returns malformed error body

- **WHEN** the backend responds with a non-2xx status and the body cannot be parsed
- **THEN** the UI displays a generic error with the HTTP status text
- **AND** no internal details are exposed

### Requirement: Role-aware UI gating

The frontend SHALL hide UI affordances the active role cannot exercise (admin-only project/knowledge actions, reviewer-only review/approval actions). The backend remains the authoritative authorization boundary; client-side gating is presentation only.

#### Scenario: Viewer cannot start a review

- **WHEN** the active session role is `viewer`
- **THEN** the review creation controls are not rendered
- **AND** navigating to `/reviews/new` shows a role-appropriate message instead of a form

#### Scenario: Non-admin cannot upload knowledge

- **WHEN** the active session role is not `admin`
- **THEN** the knowledge upload controls are not rendered

### Requirement: Project isolation in the UI

The frontend SHALL treat the active session's `projectId` as the only project the user can address. The UI SHALL NOT offer navigation that would issue a request against a different `projectId`.

#### Scenario: Active project mismatch in URL

- **WHEN** the URL `projectId` differs from the active session's `projectId`
- **THEN** the upload form is not rendered and the UI explains the mismatch

### Requirement: Idempotent human approval

The frontend SHALL generate a fresh `Idempotency-Key` for each approval or finding-decision user action. The key SHALL be surfaced in the UI so the reviewer can copy it for retry safety.

#### Scenario: Reviewer retries approval

- **WHEN** a reviewer submits the approval form and the request fails before reaching the server
- **THEN** the UI exposes the previously generated idempotency key so the reviewer can reuse it on retry
- **AND** a new click generates a new key

### Requirement: Accessible UI

All interactive components SHALL be reachable by keyboard, labeled for assistive technology, and convey state without relying on color alone.

#### Scenario: Keyboard-only navigation

- **WHEN** a user navigates the app using only the keyboard
- **THEN** every interactive control is reachable and operable

#### Scenario: Form fields have associated labels

- **WHEN** a form is rendered
- **THEN** every input has an associated `<label>` or `aria-label`

#### Scenario: Status communicated beyond color

- **WHEN** an error or success message is shown
- **THEN** the message is conveyed with text and/or `role="alert"` / `role="status"` in addition to color

### Requirement: Reference root contracts

The frontend SHALL reference root public contracts by repository-relative path (for example `openspec/specs/public-contracts/spec.md`) in code comments and `AGENTS.md`. The frontend SHALL NOT redefine HTTP endpoints, headers, or error shapes.

#### Scenario: Adding a new backend endpoint

- **WHEN** the frontend adds UI for a new backend endpoint
- **THEN** the client method signature mirrors the public contract referenced from the root spec
- **AND** no duplicate schema is added to the frontend OpenSpec store
