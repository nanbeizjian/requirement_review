import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it } from "vitest";
import { ReviewDetailPage } from "./ReviewDetailPage";
import { SessionProvider } from "../../session/SessionContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrap(node: React.ReactNode, id = "r1", role: "reviewer" | "viewer" = "reviewer") {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role }));
  return render(
    <SessionProvider>
      <MemoryRouter initialEntries={[`/reviews/${id}`]}>
        <Routes>
          <Route path="/reviews/:reviewId" element={node} />
          <Route path="/reviews/:reviewId/report" element={<div data-testid="report">report</div>} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  );
}

const baseReview = {
  review_id: "r1", project_id: "p", source_name: "spec.md",
  status: "WAITING_APPROVAL", finding_count: 2, pending_decision_count: 1,
  created_at: "2026-09-15T00:00:00Z", failed_dimensions: [],
};
const baseFindings = [
  { finding_id: "f1", requirement_id: "req-1", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L1", quote: "q" }], uses_system_fact: false, decision: null },
  { finding_id: "f2", requirement_id: "req-2", dimension: "clarity", severity: "low", issue: "i2", impact: "im2", recommendation: "rec2", confidence: 0.5, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L2", quote: "q2" }], uses_system_fact: false, decision: { action: "accept", comment: "", actor_id: "u", decided_at: "2026-09-15T01:00:00Z", idempotency_key: "k" } },
];

it("renders each finding as an independent card", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  expect(await screen.findByText(/req-1/)).toBeInTheDocument();
  expect(screen.getByText(/req-2/)).toBeInTheDocument();
});

it("filters findings by severity", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  await userEvent.selectOptions(screen.getByLabelText(/严重程度/), "high");
  expect(screen.getByText(/req-1/)).toBeInTheDocument();
  expect(screen.queryByText(/req-2/)).not.toBeInTheDocument();
});

it("shows pending count and disables approval until resolved", async () => {
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  expect(screen.getByText(/剩余 1 条待审核/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /最终确认/ })).toBeDisabled();
});

it("viewer sees read-only state with no decision controls", async () => {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" }));
  server.use(
    http.get("/api/v1/reviews/r1", () => HttpResponse.json(baseReview)),
    http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json(baseFindings)),
  );
  wrap(<ReviewDetailPage />);
  await screen.findByText(/req-1/);
  await waitFor(() => expect(screen.queryByRole("button", { name: /^接受/ })).not.toBeInTheDocument());
});
