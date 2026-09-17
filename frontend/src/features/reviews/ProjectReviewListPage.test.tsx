import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it } from "vitest";
import { ProjectReviewListPage } from "./ProjectReviewListPage";
import { SessionProvider } from "../../session/SessionContext";
import { ReviewsRefreshProvider } from "./ReviewsRefreshContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  return render(
    <SessionProvider>
      <ReviewsRefreshProvider>
        <MemoryRouter initialEntries={["/reviews"]}>
          <Routes>
            <Route path="/reviews" element={node} />
            <Route path="/reviews/:reviewId" element={<div data-testid="detail">detail</div>} />
          </Routes>
        </MemoryRouter>
      </ReviewsRefreshProvider>
    </SessionProvider>,
  );
}

it("loads and renders the review list from the API", async () => {
  server.use(http.get("/api/v1/reviews", () =>
    HttpResponse.json([
      { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 2, pending_decision_count: 1, created_at: "2026-09-15T00:00:00Z" },
    ]),
  ));
  wrap(<ProjectReviewListPage />);
  expect(await screen.findByText("a.md")).toBeInTheDocument();
  expect(screen.getByText("待人工确认")).toBeInTheDocument();
});

it("navigates to a review detail row", async () => {
  server.use(http.get("/api/v1/reviews", () =>
    HttpResponse.json([
      { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 0, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
    ]),
  ));
  wrap(<ProjectReviewListPage />);
  const row = await screen.findByRole("link", { name: /a\.md/ });
  await userEvent.click(row);
  await waitFor(() => expect(screen.getByTestId("detail")).toBeInTheDocument());
});
