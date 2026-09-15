import { newIdempotencyKey } from "./idempotency";

describe("newIdempotencyKey", () => {
  it("returns a v4-shaped UUID string", () => {
    const key = newIdempotencyKey();
    expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });
  it("produces a fresh key each call", () => {
    expect(newIdempotencyKey()).not.toBe(newIdempotencyKey());
  });
});
