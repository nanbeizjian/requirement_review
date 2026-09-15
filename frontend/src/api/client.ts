import type {
  ApprovalRequestBody,
  DataPolicy,
  FindingDecisionBody,
  Project,
  ReviewSummary,
  ReviewFinding,
} from "./types";
import { ApiError, readError } from "../lib/errors";
import type { Session } from "../session/SessionContext";

export interface ClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export class RequirementReviewClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "/api/v1").replace(/\/+$/, "");
    this.fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  }

  /** Build the standard headers required by the root public contract. */
  buildHeaders(session: Session, extra: Record<string, string> = {}): Record<string, string> {
    return {
      "X-User-ID": session.userId,
      "X-Project-ID": session.projectId,
      "X-Role": session.role,
      Accept: "application/json",
      ...extra,
    };
  }

  async createProject(
    session: Session,
    body: { name: string; data_policy: DataPolicy }
  ): Promise<Project> {
    return this.request<Project>(session, "/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async uploadKnowledge(
    session: Session,
    projectId: string,
    file: File
  ): Promise<{ document_id: string; filename: string; status: string }> {
    if (!file.name.toLowerCase().endsWith(".md") && !file.name.toLowerCase().endsWith(".markdown")) {
      throw new ApiError(415, null, "only Markdown knowledge is supported");
    }
    const form = new FormData();
    form.append("file", file);
    return this.request(session, `/projects/${encodeURIComponent(projectId)}/knowledge/documents`, {
      method: "POST",
      body: form,
    });
  }

  async createReview(
    session: Session,
    body: { project_id: string; text?: string; document_id?: string; data_policy: DataPolicy }
  ): Promise<{ review_id: string; status: string }> {
    return this.request(session, "/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async getReview(session: Session, reviewId: string): Promise<ReviewSummary> {
    return this.request<ReviewSummary>(session, `/reviews/${encodeURIComponent(reviewId)}`);
  }

  async getFindings(session: Session, reviewId: string): Promise<ReviewFinding[]> {
    return this.request<ReviewFinding[]>(session, `/reviews/${encodeURIComponent(reviewId)}/findings`);
  }

  async decideFinding(
    session: Session,
    reviewId: string,
    findingId: string,
    body: FindingDecisionBody,
    idempotencyKey: string
  ): Promise<unknown> {
    return this.request(session, `/reviews/${encodeURIComponent(reviewId)}/findings/${encodeURIComponent(findingId)}/decision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(body),
    });
  }

  async approveReview(
    session: Session,
    reviewId: string,
    body: ApprovalRequestBody,
    idempotencyKey: string
  ): Promise<{ review_id: string; status: string }> {
    return this.request(session, `/reviews/${encodeURIComponent(reviewId)}/approval`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(body),
    });
  }

  async getReport(session: Session, reviewId: string): Promise<string> {
    return this.request<string>(session, `/reviews/${encodeURIComponent(reviewId)}/report`, {}, true);
  }

  private async request<T>(
    session: Session,
    path: string,
    init: RequestInit = {},
    expectText = false
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = this.buildHeaders(session, (init.headers as Record<string, string>) ?? {});
    const response = await this.fetchImpl(url, { ...init, headers });
    if (!response.ok) {
      throw await readError(response);
    }
    if (expectText) {
      return (await response.text()) as unknown as T;
    }
    if (response.status === 204) {
      return undefined as unknown as T;
    }
    return (await response.json()) as T;
  }
}

/**
 * Generate a fresh per-action idempotency key. Surfacing this in the UI prevents
 * accidental retries from producing duplicate approval/decision records.
 */
export function newIdempotencyKey(prefix: string): string {
  const random = Math.random().toString(36).slice(2, 10);
  const time = Date.now().toString(36);
  return `${prefix}-${time}-${random}`;
}
