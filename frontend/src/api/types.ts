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
