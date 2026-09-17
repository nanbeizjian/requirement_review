import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it, vi } from "vitest";
import { DirectoryPicker } from "./DirectoryPicker";
import { SessionProvider } from "../../session/SessionContext";
import { ReviewsRefreshProvider } from "../reviews/ReviewsRefreshContext";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrap(node: React.ReactNode) {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role: "reviewer" }));
  server.use(http.post("/api/v1/reviews", () => HttpResponse.json({ review_id: "r", status: "PENDING" }, { status: 202 })));
  return render(
    <SessionProvider>
      <ReviewsRefreshProvider>{node}</ReviewsRefreshProvider>
    </SessionProvider>,
  );
}

it("renders a directory input and a multi-file fallback", () => {
  wrap(<DirectoryPicker onReady={() => {}} />);
  expect(screen.getByTestId("dir-input")).toBeInTheDocument();
  expect(screen.getByTestId("files-input")).toBeInTheDocument();
});

it("surfaces ignored file count after selection via dir-input (no accept filter)", async () => {
  const onReady = vi.fn();
  wrap(<DirectoryPicker onReady={onReady} />);
  const md = new File(["x"], "a.md", { type: "text/markdown" });
  const other = new File(["y"], "b.txt", { type: "text/plain" });
  await userEvent.upload(screen.getByTestId("dir-input"), [md, other]);
  await waitFor(() => expect(screen.getByText(/忽略 1 个非 Markdown 文件/)).toBeInTheDocument());
  expect(onReady).toHaveBeenCalled();
  const arg = onReady.mock.calls[0]![0] as Array<{ name: string; text: string }>;
  expect(arg.map((f) => f.name)).toEqual(["a.md"]);
});
