import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ProjectReviewListPage } from "./ProjectReviewListPage";
import { SessionProvider } from "../../session/SessionContext";
import { ReviewsRefreshProvider, useReviewsRefresher } from "./ReviewsRefreshContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function RefreshButton() {
  const { requestRefresh } = useReviewsRefresher();
  return <button onClick={() => requestRefresh()}>refresh</button>;
}

function wrap(node: ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(
    <SessionProvider>
      <ReviewsRefreshProvider>
        <MemoryRouter initialEntries={["/reviews"]}>
          <Routes>
            <Route path="/reviews" element={<>{node}<RefreshButton /></>} />
            <Route path="/reviews/:reviewId" element={<div data-testid="detail">detail</div>} />
          </Routes>
        </MemoryRouter>
      </ReviewsRefreshProvider>
    </SessionProvider>,
  );
}

describe("ProjectReviewListPage refresh integration", () => {
  it("loads the initial list on mount", async () => {
    server.use(http.get("/api/v1/reviews", () =>
      HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
      ]),
    ));
    wrap(<ProjectReviewListPage />);
    expect(await screen.findByText("a.md")).toBeInTheDocument();
  });

  it("refetches when refreshCounter changes (counter 0 → 1)", async () => {
    let hits = 0;
    server.use(http.get("/api/v1/reviews", () => {
      hits += 1;
      const list = hits === 1
        ? [{ review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" }]
        : [
            { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
            { review_id: "r2", project_id: "p", source_name: "b.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
          ];
      return HttpResponse.json(list);
    }));
    wrap(<ProjectReviewListPage />);
    await screen.findByText("a.md");
    expect(hits).toBe(1);
    await userEvent.click(screen.getByRole("button", { name: /refresh/ }));
    await screen.findByText("b.md");
    expect(hits).toBe(2);
  });

  it("coalesces back-to-back refreshCounter increments to a single extra fetch", async () => {
    let hits = 0;
    server.use(http.get("/api/v1/reviews", async () => {
      hits += 1;
      // each fetch takes a moment so a second concurrent refresh has time to fire
      await new Promise((r) => setTimeout(r, 30));
      return HttpResponse.json([]);
    }));
    function Bumper() {
      const { requestRefresh } = useReviewsRefresher();
      return (
        <>
          <button onClick={() => { requestRefresh(); requestRefresh(); requestRefresh(); }}>burst</button>
        </>
      );
    }
    sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
    render(
      <SessionProvider>
        <ReviewsRefreshProvider>
          <MemoryRouter initialEntries={["/reviews"]}>
            <Routes>
              <Route path="/reviews" element={<><ProjectReviewListPage /><Bumper /></>} />
            </Routes>
          </MemoryRouter>
        </ReviewsRefreshProvider>
      </SessionProvider>,
    );
    await waitFor(() => expect(hits).toBeGreaterThanOrEqual(1));
    const before = hits;
    await userEvent.click(screen.getByRole("button", { name: /burst/ }));
    await waitFor(() => expect(hits).toBeGreaterThanOrEqual(before + 1));
    // wait a bit more to ensure no second fetch fires from coalescing
    await new Promise((r) => setTimeout(r, 80));
    expect(hits).toBeLessThanOrEqual(before + 1);
  });

  it("keeps the previous rows visible when a refresh request fails", async () => {
    let n = 0;
    server.use(http.get("/api/v1/reviews", () => {
      n += 1;
      if (n === 1) return HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
      ]);
      return HttpResponse.json({ code: "boom", message: "down", correlation_id: "c1" }, { status: 503 });
    }));
    wrap(<ProjectReviewListPage />);
    await screen.findByText("a.md");
    await userEvent.click(screen.getByRole("button", { name: /refresh/ }));
    // list still shows a.md
    expect(await screen.findByText("a.md")).toBeInTheDocument();
    // error alert surfaces the safe message and correlation id
    expect(await screen.findByText(/down/)).toBeInTheDocument();
    expect(await screen.findByText(/c1/)).toBeInTheDocument();
  });
});
