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
