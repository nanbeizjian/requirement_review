# Public Contracts Specification

## Purpose

Define repository-wide contracts shared by clients, backend services, and future integrations.

## Requirements

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

### Requirement: Project isolation

Every public operation SHALL be scoped to an authenticated project identity. A caller SHALL NOT read or mutate another project's requirements, knowledge, reviews, findings, decisions, or reports.

#### Scenario: Cross-project access is attempted

- **WHEN** an authenticated caller requests a resource owned by another project
- **THEN** the operation is rejected without disclosing the resource contents

### Requirement: Human approval

A review report SHALL NOT become final until an authorized human reviewer explicitly approves it. Approval and rejection operations SHALL be auditable and idempotent.

For the `POST /api/v1/reviews/{review_id}/approval` endpoint, "idempotent" SHALL mean:

- If a request reuses an `Idempotency-Key` whose stored payload matches the new request payload exactly (same `action`, `comment`, `dimensions`, and `findings`), the backend SHALL return the original response status and body without re-executing the review graph, and SHALL NOT record a second approval entry.
- If a request reuses an `Idempotency-Key` with a different payload, the backend SHALL reject the request with a `409` response whose stable error code is `idempotency_conflict` and whose correlation identifier is the offending `Idempotency-Key`.

#### Scenario: Automated review completes

- **WHEN** all automated review dimensions finish successfully
- **THEN** the review enters a human-approval state
- **AND** no final report is published before an authorized approval

#### Scenario: Same Idempotency-Key, identical body

- **WHEN** a client retries the approval request with the same `Idempotency-Key` and the same `action`, `comment`, `dimensions`, and `findings`
- **THEN** the backend returns the original response and does not append a second approval entry to the report
- **AND** no additional graph resume occurs

#### Scenario: Same Idempotency-Key, different body

- **WHEN** a client sends a second approval request reusing the same `Idempotency-Key` with a different `action`, `comment`, `dimensions`, or `findings`
- **THEN** the backend rejects the request with a `409` response
- **AND** the response carries the stable error code `idempotency_conflict`
- **AND** the response includes the offending `Idempotency-Key` as the correlation identifier
- **AND** the previously stored approval remains the only approval on the review

### Requirement: Evidence traceability

Every review finding SHALL include a source document identifier, source version, stable locator, and source quote that can be verified against the referenced content.

#### Scenario: Evidence cannot be verified

- **WHEN** a finding's locator or quote does not match the referenced source version
- **THEN** the finding is marked invalid
- **AND** it cannot be included in an approved final report

### Requirement: Compatible errors

Public API errors SHALL use a stable machine-readable code, a safe human-readable message, and a request correlation identifier. Internal stack traces and secrets SHALL NOT be exposed.

#### Scenario: Backend operation fails

- **WHEN** a public API operation fails
- **THEN** the response contains the stable error contract
- **AND** diagnostic details remain in server-side telemetry only

### Requirement: Model provider configuration compatibility
The backend SHALL support provider-agnostic model runtime configuration for automated review model calls while preserving existing MiniMax-specific configuration as a backwards-compatible fallback. Provider-agnostic settings SHALL take precedence over provider-specific fallback settings when both are present.

#### Scenario: Generic configuration selects a provider
- **WHEN** the backend starts with provider-agnostic model settings for a supported provider
- **THEN** automated review model calls use the configured provider, model name, base URL, credentials, timeout, retry, and concurrency settings
- **AND** provider credentials are not exposed through public API responses, frontend bundles, or logs

#### Scenario: Existing MiniMax configuration remains usable
- **WHEN** the backend starts without provider-agnostic model settings but with the existing MiniMax-specific settings
- **THEN** automated review model calls continue to use MiniMax-compatible behavior
- **AND** no existing MiniMax deployment is required to rename secrets before it can start

### Requirement: Safe model provider errors
The backend SHALL map model-provider failures into stable safe error categories for review workflow state and telemetry. Public API responses SHALL NOT expose provider credentials, document bodies, stack traces, or raw upstream responses.

#### Scenario: Upstream provider rate-limits a review
- **WHEN** the configured model provider returns a rate-limit response during automated review
- **THEN** the review workflow records a safe provider error category for the affected model-call scope
- **AND** public API responses expose only stable review status and safe failure summaries

#### Scenario: Provider returns malformed model output
- **WHEN** a provider response cannot be parsed or validated as review findings
- **THEN** the affected model-call scope is marked with a safe parse or bad-response category
- **AND** valid findings from other successful scopes remain eligible for review consolidation

### Requirement: Bounded model provider concurrency
The backend SHALL bound concurrent upstream model calls made by automated review workflows. Rate-limit and transient upstream failures SHALL be retried with bounded backoff according to configuration before the affected scope is marked failed.

#### Scenario: Full-document review creates many model calls
- **WHEN** a review document produces multiple requirement items and dimensions
- **THEN** the backend limits simultaneous provider calls to the configured concurrency
- **AND** transient provider errors are retried without exceeding configured retry limits

#### Scenario: One model call fails after retries
- **WHEN** a single requirement or dimension model call exhausts its configured retries
- **THEN** that failure does not discard unrelated successful findings from other model-call scopes
- **AND** the review summary identifies only the dimensions that still contain failed scopes
