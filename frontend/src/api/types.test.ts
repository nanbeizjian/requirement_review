import { isTerminalStatus, ROLE_VALUES, DATA_POLICY_VALUES } from "./types";

describe("api/types", () => {
  it("treats WAITING_APPROVAL, COMPLETED, FAILED as terminal", () => {
    expect(isTerminalStatus("WAITING_APPROVAL")).toBe(true);
    expect(isTerminalStatus("COMPLETED")).toBe(true);
    expect(isTerminalStatus("FAILED")).toBe(true);
    expect(isTerminalStatus("REVIEWING")).toBe(false);
    expect(isTerminalStatus("PENDING")).toBe(false);
  });

  it("exposes the canonical role set", () => {
    expect([...ROLE_VALUES].sort()).toEqual(["admin", "reviewer", "viewer"]);
  });

  it("exposes the canonical data policy set", () => {
    expect([...DATA_POLICY_VALUES].sort()).toEqual(["cloud_allowed", "cloud_redacted", "local_only"]);
  });
});
