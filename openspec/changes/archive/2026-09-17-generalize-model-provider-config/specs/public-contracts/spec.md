## ADDED Requirements

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
