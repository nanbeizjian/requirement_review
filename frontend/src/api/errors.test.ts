import { parseApiError, ApiError } from "./errors";

describe("parseApiError", () => {
  it("decodes a 409 conflict envelope", async () => {
    const res = new Response(JSON.stringify({ code: "idempotency_conflict", message: "conflict", correlation_id: "abc" }), { status: 409 });
    const err = await parseApiError(res);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.code).toBe("idempotency_conflict");
    expect(err.message).toBe("conflict");
    expect(err.correlationId).toBe("abc");
  });
  it("falls back to status text when envelope missing", async () => {
    const res = new Response("not json", { status: 500 });
    const err = await parseApiError(res);
    expect(err.code).toBe("http_500");
    expect(err.correlationId).toBe("");
  });
});
