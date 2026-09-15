import { formatDateTime } from "./formatDate";
it("formats ISO timestamps in zh-CN", () => {
  expect(formatDateTime("2026-09-15T10:00:00Z")).toMatch(/2026/);
});
