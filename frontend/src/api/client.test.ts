import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ApiError, apiClient, type Actor } from "./client";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const actor: Actor = { userId: "u1", projectId: "p1", role: "reviewer" };

describe("apiClient", () => {
  it("injects identity headers on every request", async () => {
    let received: Record<string, string> = {};
    server.use(
      http.get("/api/v1/reviews", ({ request }) => {
        received = {
          user: request.headers.get("X-User-ID") ?? "",
          project: request.headers.get("X-Project-ID") ?? "",
          role: request.headers.get("X-Role") ?? "",
        };
        return HttpResponse.json([]);
      }),
    );
    await apiClient.listReviews(actor);
    expect(received).toEqual({ user: "u1", project: "p1", role: "reviewer" });
  });

  it("auto-generates an idempotency key when none supplied", async () => {
    let key = "";
    server.use(
      http.post("/api/v1/reviews", ({ request }) => {
        key = request.headers.get("Idempotency-Key") ?? "";
        return HttpResponse.json({ review_id: "r1", status: "PENDING" }, { status: 202 });
      }),
    );
    await apiClient.createReview(actor, { project_id: "p1", data_policy: "local_only", text: "x", source_name: "a.md" });
    expect(key).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("preserves a caller-supplied idempotency key for retries", async () => {
    let count = 0;
    server.use(
      http.post("/api/v1/reviews/x/findings/y/decision", ({ request }) => {
        count += 1;
        const k = request.headers.get("Idempotency-Key");
        if (count === 1) return new HttpResponse(null, { status: 502 });
        return HttpResponse.json({}, { headers: { "Idempotency-Key": k ?? "" } });
      }),
    );
    await expect(
      apiClient.decideFinding(actor, "x", "y", { action: "accept", comment: "ok" }, { idempotencyKey: "stable-key", retry: { retries: 1, baseDelayMs: 1 } }),
    ).rejects.toBeInstanceOf(ApiError);
    await apiClient.decideFinding(actor, "x", "y", { action: "accept", comment: "ok" }, { idempotencyKey: "stable-key", retry: { retries: 1, baseDelayMs: 1 } });
    expect(count).toBe(2);
  });

  it("decodes the error envelope on non-2xx", async () => {
    server.use(
      http.post("/api/v1/reviews", () =>
        HttpResponse.json({ code: "validation_failed", message: "bad input", correlation_id: "cid-1" }, { status: 422 }),
      ),
    );
    await expect(
      apiClient.createReview(actor, { project_id: "p1", data_policy: "local_only", text: "x", source_name: "a.md" }),
    ).rejects.toMatchObject({ status: 422, code: "validation_failed", correlationId: "cid-1" });
  });

  it("honors AbortSignal to cancel in-flight requests", async () => {
    server.use(http.get("/api/v1/reviews", () => new HttpResponse(null, { status: 200, headers: { "Content-Type": "application/json" } })));
    const ac = new AbortController();
    ac.abort();
    await expect(apiClient.listReviews(actor, { signal: ac.signal })).rejects.toThrow();
  });
});
