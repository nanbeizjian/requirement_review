import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import App from "./App";
import { MemoryRouter } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("App integration", () => {
  it("loads list and finding decisions from the server on re-entry", async () => {
    sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
    server.use(
      http.get("/api/v1/reviews", () => HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z" },
      ])),
      http.get("/api/v1/reviews/r1", () => HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "2026-09-15T00:00:00Z", failed_dimensions: [] })),
      http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json([
        { finding_id: "f1", requirement_id: "r", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }], uses_system_fact: false, decision: { action: "accept", comment: "ok", actor_id: "u", decided_at: "t", idempotency_key: "k" } },
      ])),
    );
    const { unmount } = render(<MemoryRouter initialEntries={["/reviews"]}><App /></MemoryRouter>);
    await screen.findByText("a.md");
    unmount();
    render(<MemoryRouter initialEntries={["/reviews"]}><App /></MemoryRouter>);
    await screen.findByText("a.md");
    await userEvent.click(screen.getByRole("link", { name: /a\.md/ }));
    await waitFor(() => expect(screen.getByText(/ok/)).toBeInTheDocument());
  });

  it.skip("surfaces 409 idempotency_conflict to the user without crashing", async () => {
    sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
    server.use(
      http.get("/api/v1/reviews", () => HttpResponse.json([
        { review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "t" },
      ])),
      http.get("/api/v1/reviews/r1", () => HttpResponse.json({ review_id: "r1", project_id: "p", source_name: "a.md", status: "WAITING_APPROVAL", finding_count: 1, pending_decision_count: 0, created_at: "t", failed_dimensions: [] })),
      http.get("/api/v1/reviews/r1/findings", () => HttpResponse.json([
        { finding_id: "f1", requirement_id: "r", dimension: "completeness", severity: "high", issue: "i", impact: "im", recommendation: "rec", confidence: 0.9, evidence: [{ source_type: "requirement", document_id: "d", version: 1, locator: "L", quote: "q" }], uses_system_fact: false, decision: null },
      ])),
      http.post("/api/v1/reviews/r1/findings/f1/decision", () => HttpResponse.json({ code: "idempotency_conflict", message: "key reused with different body", correlation_id: "cid-9" }, { status: 409 })),
    );
    render(<MemoryRouter initialEntries={["/reviews"]}><App /></MemoryRouter>);
    await userEvent.click(await screen.findByRole("link", { name: /a\.md/ }));
    await userEvent.click(await screen.findByRole("button", { name: /接受/ }));
    await userEvent.click(screen.getByRole("button", { name: /提交决策/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/key reused/);
  });
});
