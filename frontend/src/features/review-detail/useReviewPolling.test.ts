import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, expect, it } from "vitest";
import { useReviewPolling } from "./useReviewPolling";
import { TestWrap } from "./_test-wrap";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

beforeEach(() => sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" })));

const baseReview = {
  review_id: "r1", project_id: "p", source_name: "x.md",
  status: "REVIEWING" as const, finding_count: 0, pending_decision_count: 0,
  created_at: "2026-09-15T00:00:00Z", failed_dimensions: [],
};

describe("useReviewPolling", () => {
  it("exposes the initial fetched status as data.status", async () => {
    server.use(http.get("/api/v1/reviews/r1", () => HttpResponse.json({ ...baseReview })));
    const { result } = renderHook(() => useReviewPolling("r1", { initialMs: 1000 }), { wrapper: TestWrap });
    await waitFor(() => expect(result.current.data?.status).toBe("REVIEWING"));
  });

  it("stops on terminal status (no further calls)", async () => {
    let calls = 0;
    server.use(http.get("/api/v1/reviews/r1", () => {
      calls += 1;
      return HttpResponse.json({ ...baseReview, status: "WAITING_APPROVAL" });
    }));
    renderHook(() => useReviewPolling("r1", { initialMs: 50 }), { wrapper: TestWrap });
    await waitFor(() => expect(calls).toBe(1));
    await new Promise((r) => setTimeout(r, 200));
    expect(calls).toBe(1);
  });

  it("marks stale after consecutive errors and exposes retry", async () => {
    server.use(http.get("/api/v1/reviews/r1", () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useReviewPolling("r1", { initialMs: 5, maxMs: 5, staleAfter: 3 }), { wrapper: TestWrap });
    await waitFor(() => expect(result.current.stale).toBe(true), { timeout: 3000 });
    expect(typeof result.current.retry).toBe("function");
  });

  it("does not poll when reviewId is null", async () => {
    let calls = 0;
    server.use(http.get("/api/v1/reviews/r1", () => { calls += 1; return HttpResponse.json({ ...baseReview }); }));
    const { result } = renderHook(() => useReviewPolling(null), { wrapper: TestWrap });
    await new Promise((r) => setTimeout(r, 50));
    expect(calls).toBe(0);
    expect(result.current.data).toBeNull();
  });
});
