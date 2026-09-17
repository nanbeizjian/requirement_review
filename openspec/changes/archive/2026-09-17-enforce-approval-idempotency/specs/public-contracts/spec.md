## MODIFIED Requirements

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
