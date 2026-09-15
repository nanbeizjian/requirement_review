import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { useDirectorySubmission } from "./useDirectorySubmission";
import { TestWrap } from "./_test-wrap";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const actor = { userId: "u", projectId: "p", role: "reviewer" as const };
sessionStorage.setItem("rr:session:v1", JSON.stringify(actor));

describe("useDirectorySubmission", () => {
  it("caps concurrency at 3 and submits every file", async () => {
    let inflight = 0;
    let maxInflight = 0;
    let finished = 0;
    server.use(http.post("/api/v1/reviews", async () => {
      inflight += 1;
      maxInflight = Math.max(maxInflight, inflight);
      await new Promise((r) => setTimeout(r, 30));
      inflight -= 1;
      finished += 1;
      return HttpResponse.json({ review_id: `r${finished}`, status: "PENDING" }, { status: 202 });
    }));
    const files = Array.from({ length: 6 }, (_, i) => ({ name: `f${i}.md`, text: "x" }));
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 3 }), { wrapper: TestWrap });
    await act(async () => { await result.current.submit(files); });
    await waitFor(() => expect(result.current.summary.completed).toBe(6));
    expect(maxInflight).toBeLessThanOrEqual(3);
    expect(result.current.summary.failed).toBe(0);
  });

  it("isolates per-file failure without blocking others", async () => {
    let n = 0;
    server.use(http.post("/api/v1/reviews", () => {
      n += 1;
      if (n === 2) return HttpResponse.json({ code: "x", message: "bad", correlation_id: "c" }, { status: 422 });
      return HttpResponse.json({ review_id: `r${n}`, status: "PENDING" }, { status: 202 });
    }));
    const files = Array.from({ length: 4 }, (_, i) => ({ name: `f${i}.md`, text: "x" }));
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 2 }), { wrapper: TestWrap });
    await act(async () => { await result.current.submit(files); });
    await waitFor(() => expect(result.current.summary.completed + result.current.summary.failed).toBe(4));
    expect(result.current.summary.failed).toBe(1);
    expect(result.current.summary.completed).toBe(3);
  });

  it("does not include absolute paths in the request body", async () => {
    let body: { source_name?: string; text?: string } = {};
    server.use(http.post("/api/v1/reviews", async ({ request }) => {
      body = (await request.json()) as typeof body;
      return HttpResponse.json({ review_id: "r", status: "PENDING" }, { status: 202 });
    }));
    const { result } = renderHook(() => useDirectorySubmission(), { wrapper: TestWrap });
    await act(async () => { await result.current.submit([{ name: "/Users/u/secret/SPEC.md", text: "x" }]); });
    expect(body.source_name).toBe("SPEC.md");
    expect(body.text).toBe("x");
    expect(JSON.stringify(body)).not.toContain("/Users/u/secret");
  });
});
