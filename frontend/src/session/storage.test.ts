import { readSession, writeSession, clearSession, SESSION_STORAGE_KEY } from "./storage";

describe("session storage", () => {
  beforeEach(() => sessionStorage.clear());
  it("returns null when no session is stored", () => {
    expect(readSession()).toBeNull();
  });
  it("round-trips a valid session", () => {
    writeSession({ userId: "u", projectId: "p", role: "reviewer" });
    expect(readSession()).toEqual({ userId: "u", projectId: "p", role: "reviewer" });
  });
  it("rejects invalid stored payloads", () => {
    sessionStorage.setItem(SESSION_STORAGE_KEY, "{not json");
    expect(readSession()).toBeNull();
  });
  it("clearSession removes the entry", () => {
    writeSession({ userId: "u", projectId: "p", role: "viewer" });
    clearSession();
    expect(readSession()).toBeNull();
  });
});
