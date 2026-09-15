import { newIdempotencyKey } from "./idempotency";
import { parseApiError } from "./errors";
export { ApiError } from "./errors";
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
    if (!res.ok) throw await parseApiError(res);
    return (await res.json()) as T;
  }
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
