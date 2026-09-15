import { render, screen } from "@testing-library/react";
import { RoleGate } from "./RoleGate";
import { SessionProvider } from "../session/SessionContext";

function wrap(role: "admin" | "reviewer" | "viewer" | null) {
  if (role) sessionStorage.setItem("rr:session:v1", JSON.stringify({ userId: "u", projectId: "p", role }));
  else sessionStorage.clear();
  return render(
    <SessionProvider>
      <RoleGate allow={["reviewer", "admin"]} fallback={<span>read-only</span>}>
        <span>action</span>
      </RoleGate>
    </SessionProvider>,
  );
}

it("renders children when role is allowed", () => { wrap("reviewer"); expect(screen.getByText("action")).toBeInTheDocument(); });
it("renders fallback for viewer", () => { wrap("viewer"); expect(screen.getByText("read-only")).toBeInTheDocument(); });
it("renders fallback when no session", () => { wrap(null); expect(screen.getByText("read-only")).toBeInTheDocument(); });
