import { describe, it, expect } from "vitest";
import { RequirementReviewClient } from "../api/client";
import { ApiError } from "../lib/errors";
import type { Session } from "../session/SessionContext";

const session: Session = { userId: "alice", projectId: "proj-1", role: "reviewer" };

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("RequirementReviewClient", () => {
  it("injects X-User-ID, X-Project-ID, X-Role on every request", async () => {
    const seen: Array<{ url: string; headers: Record<string, string> }> = [];
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const headers: Record<string, string> = {};
      const initHeaders = init?.headers as Record<string, string> | undefined;
      if (initHeaders) {
        Object.entries(initHeaders).forEach(([k, v]) => (headers[k] = v as string));
      } else if (input instanceof Request) {
        input.headers.forEach((v, k) => (headers[k] = v));
      }
      seen.push({ url, headers });
      return jsonResponse(200, { review_id: "r1", status: "PENDING" });
    };
    const client = new RequirementReviewClient({ fetchImpl });
    await client.createReview(session, {
      project_id: "proj-1",
      text: "# hi",
      data_policy: "local_only",
    });
    expect(seen).toHaveLength(1);
    expect(seen[0].url).toBe("/api/v1/reviews");
    expect(seen[0].headers["X-User-ID"]).toBe("alice");
    expect(seen[0].headers["X-Project-ID"]).toBe("proj-1");
    expect(seen[0].headers["X-Role"]).toBe("reviewer");
  });

  it("attaches Idempotency-Key to approval requests", async () => {
    const seen: Array<Record<string, string>> = [];
    const fetchImpl: typeof fetch = async (_input, init) => {
      const headers = init?.headers as Record<string, string>;
      seen.push(headers);
      return jsonResponse(202, { review_id: "r1", status: "APPROVED" });
    };
    const client = new RequirementReviewClient({ fetchImpl });
    await client.approveReview(
      session,
      "r1",
      { action: "approve", comment: "ok" },
      "approval-xyz"
    );
    expect(seen[0]["Idempotency-Key"]).toBe("approval-xyz");
  });

  it("maps non-2xx responses to ApiError with stable contract fields", async () => {
    const fetchImpl: typeof fetch = async () =>
      jsonResponse(403, {
        code: "forbidden_role",
        message: "reviewer role required",
        correlation_id: "corr-1",
      });
    const client = new RequirementReviewClient({ fetchImpl });
    await expect(
      client.getReview(session, "r1")
    ).rejects.toBeInstanceOf(ApiError);
    try {
      await client.getReview(session, "r1");
    } catch (err) {
      const e = err as ApiError;
      expect(e.code).toBe("forbidden_role");
      expect(e.correlationId).toBe("corr-1");
      expect(e.status).toBe(403);
    }
  });

  it("rejects non-Markdown knowledge uploads with status 415", async () => {
    const client = new RequirementReviewClient({
      fetchImpl: (() => {
        throw new Error("fetch should not be called for invalid uploads");
      }) as unknown as typeof fetch,
    });
    const pdf = new File(["binary"], "spec.pdf", { type: "application/pdf" });
    await expect(
      client.uploadKnowledge(session, "proj-1", pdf)
    ).rejects.toMatchObject({ status: 415 });
  });
});
