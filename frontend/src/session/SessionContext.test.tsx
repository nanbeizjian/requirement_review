import { render, screen } from "@testing-library/react";
import { SessionProvider, useSession } from "./SessionContext";

function Probe() {
  const s = useSession();
  return <span>{s.actor?.userId ?? "anonymous"}</span>;
}

it("provides null when no session is stored", () => {
  sessionStorage.clear();
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(screen.getByText("anonymous")).toBeInTheDocument();
});

it("exposes the stored session to consumers", () => {
  sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u1", projectId: "p1", role: "reviewer" }));
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(screen.getByText("u1")).toBeInTheDocument();
});
