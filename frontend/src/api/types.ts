// Mirrors backend Pydantic schemas in backend/src/requirement_review/api/schemas.py
// and backend/src/requirement_review/domain/models.py. Field names are part of the
// root public contract (see openspec/specs/public-contracts/spec.md).

export type Role = "admin" | "reviewer" | "viewer";

export type DataPolicy = "local_only" | "cloud_allowed" | "cloud_redacted";

export type ReviewStatus = "PENDING" | "AWAITING_APPROVAL" | "COMPLETED" | "FAILED";

export type ReviewDimension =
  | "completeness"
  | "consistency"
  | "clarity"
  | "feasibility"
  | "testability"
  | "security"
  | "performance"
  | "data_interface";

export type Severity = "critical" | "high" | "medium" | "low";

export type FindingAction = "accept" | "reject" | "re-review";

export type ApprovalAction = "approve" | "modify" | "reject" | "re-review";

export interface EvidenceRef {
  source_type: string;
  document_id: string;
  version: number;
  locator: string;
  quote: string;
}

export interface ReviewFinding {
  finding_id?: string | null;
  requirement_id: string;
  dimension: ReviewDimension;
  severity: Severity;
  issue: string;
  impact: string;
  recommendation: string;
  confidence: number;
  evidence: EvidenceRef[];
  uses_system_fact: boolean;
}

export interface Project {
  id: string;
  name: string;
  data_policy: DataPolicy;
  owner: string;
}

export interface ReviewSummary {
  review_id: string;
  project_id: string;
  status: ReviewStatus;
  failed_dimensions: ReviewDimension[];
}

export interface ApprovalRequestBody {
  action: ApprovalAction;
  comment?: string;
  dimensions?: ReviewDimension[];
  findings?: Record<string, unknown>[];
}

export interface FindingDecisionBody {
  action: FindingAction;
  comment?: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  correlation_id: string;
}
