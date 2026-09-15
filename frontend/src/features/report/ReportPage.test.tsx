import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it } from "vitest";
import { ReportPage } from "./ReportPage";
import { SessionProvider } from "../../session/SessionContext";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("renders escaped markdown report text", async () => {
  server.use(http.get("/api/v1/reviews/r1/report", () =>
    new HttpResponse("# Final Report\n<script>alert(1)</script>", { headers: { "Content-Type": "text/markdown" } }),
  ));
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "viewer" }));
  render(
    <SessionProvider>
      <MemoryRouter initialEntries={["/reviews/r1/report"]}>
        <Routes>
          <Route path="/reviews/:reviewId/report" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    </SessionProvider>,
  );
  const region = await screen.findByRole("region", { name: /报告内容/ });
  expect(region.textContent).toContain("Final Report");
  expect(region.innerHTML).not.toContain("<script>");
});
