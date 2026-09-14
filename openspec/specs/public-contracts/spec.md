# Public Contracts Specification

## Purpose

Define repository-wide contracts shared by clients, backend services, and future integrations.

## Requirements

### Requirement: Root contract authority

The repository-root `openspec/specs/` directory SHALL be the authoritative source for public contracts. Component specifications SHALL reference these contracts and SHALL NOT define conflicting copies.

#### Scenario: Backend consumes a public contract

- **WHEN** a backend change uses an HTTP schema, authorization rule, shared domain model, or error response
- **THEN** the backend specification references the applicable root contract
- **AND** any contract modification is proposed in the root OpenSpec store

### Requirement: Project isolation

Every public operation SHALL be scoped to an authenticated project identity. A caller SHALL NOT read or mutate another project's requirements, knowledge, reviews, findings, decisions, or reports.

#### Scenario: Cross-project access is attempted

- **WHEN** an authenticated caller requests a resource owned by another project
- **THEN** the operation is rejected without disclosing the resource contents

### Requirement: Human approval

A review report SHALL NOT become final until an authorized human reviewer explicitly approves it. Approval and rejection operations SHALL be auditable and idempotent.

#### Scenario: Automated review completes

- **WHEN** all automated review dimensions finish successfully
- **THEN** the review enters a human-approval state
- **AND** no final report is published before an authorized approval

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
