import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

it.each([
  ["PENDING", "等待中"],
  ["PARSING", "解析中"],
  ["RETRIEVING", "检索知识"],
  ["REVIEWING", "评审中"],
  ["CONSOLIDATING", "汇总中"],
  ["WAITING_APPROVAL", "待人工确认"],
  ["COMPLETED", "已完成"],
  ["FAILED", "失败"],
] as const)("translates %s to %s", (status, label) => {
  render(<StatusBadge status={status} />);
  expect(screen.getByText(label)).toBeInTheDocument();
});
