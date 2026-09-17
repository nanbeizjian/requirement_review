import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { useDirectorySubmission } from "./useDirectorySubmission";
import { ReviewsRefreshProvider, useReviewsRefresher } from "../reviews/ReviewsRefreshContext";
import { SessionProvider } from "../../session/SessionContext";
import type { ReactNode } from "react";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const actor = { userId: "u", projectId: "p", role: "reviewer" as const };
sessionStorage.setItem("rr:session:v1", JSON.stringify(actor));

function makeWrapper() {
  let latest: { refreshCounter: number; requestRefresh: () => void } | null = null;
  function Probe() {
    latest = useReviewsRefresher();
    return null;
  }
  function Harness({ children }: { children: ReactNode }) {
    return (
      <SessionProvider>
        <ReviewsRefreshProvider>
          <Probe />
          {children}
        </ReviewsRefreshProvider>
      </SessionProvider>
    );
  }
  return {
    wrapper: Harness,
    getRefresher: () => {
      if (!latest) throw new Error("refresher not captured yet");
      return latest;
    },
  };
}

describe("useDirectorySubmission → refresh signal", () => {
  it("calls requestRefresh once after a successful submission", async () => {
    server.use(http.post("/api/v1/reviews", () =>
      HttpResponse.json({ review_id: "r", status: "PENDING" }, { status: 202 })));
    const { wrapper, getRefresher } = makeWrapper();
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 1 }), { wrapper });
    await act(async () => { await result.current.submit([{ name: "a.md", text: "x" }]); });
    expect(getRefresher().refreshCounter).toBe(1);
  });

  it("coalesces multiple successful submissions into a single increment within the same tick", async () => {
    server.use(http.post("/api/v1/reviews", () =>
      HttpResponse.json({ review_id: "r", status: "PENDING" }, { status: 202 })));
    const { wrapper, getRefresher } = makeWrapper();
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 1 }), { wrapper });
    await act(async () => {
      await result.current.submit([
        { name: "a.md", text: "x" },
        { name: "b.md", text: "y" },
      ]);
    });
    expect(getRefresher().refreshCounter).toBe(1);
  });

  it("does not call requestRefresh when every submission fails", async () => {
    server.use(http.post("/api/v1/reviews", () =>
      HttpResponse.json({ code: "x", message: "bad", correlation_id: "c" }, { status: 422 })));
    const { wrapper, getRefresher } = makeWrapper();
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 1 }), { wrapper });
    await act(async () => { await result.current.submit([{ name: "a.md", text: "x" }]); });
    expect(getRefresher().refreshCounter).toBe(0);
    expect(result.current.summary.failed).toBe(1);
  });

  it("calls requestRefresh only for successful files when batch mixes success and failure", async () => {
    let n = 0;
    server.use(http.post("/api/v1/reviews", () => {
      n += 1;
      if (n === 2) return HttpResponse.json({ code: "x", message: "bad", correlation_id: "c" }, { status: 422 });
      return HttpResponse.json({ review_id: `r${n}`, status: "PENDING" }, { status: 202 });
    }));
    const { wrapper, getRefresher } = makeWrapper();
    const { result } = renderHook(() => useDirectorySubmission({ concurrency: 1 }), { wrapper });
    await act(async () => {
      await result.current.submit([
        { name: "a.md", text: "x" },
        { name: "b.md", text: "y" },
      ]);
    });
    expect(result.current.summary.completed).toBe(1);
    expect(result.current.summary.failed).toBe(1);
    expect(getRefresher().refreshCounter).toBe(1);
  });
});
