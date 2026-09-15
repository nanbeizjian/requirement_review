import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

it("renders with accessible name and fires onClick", async () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>提交</Button>);
  const btn = screen.getByRole("button", { name: /提交/ });
  await userEvent.click(btn);
  expect(onClick).toHaveBeenCalledTimes(1);
});

it("disables interaction when disabled", async () => {
  const onClick = vi.fn();
  render(<Button disabled onClick={onClick}>提交</Button>);
  await userEvent.click(screen.getByRole("button", { name: /提交/ }));
  expect(onClick).not.toHaveBeenCalled();
});

it("forwards aria-label to the rendered button", () => {
  render(<Button aria-label="提交当前文件">→</Button>);
  expect(screen.getByRole("button", { name: "提交当前文件" })).toBeInTheDocument();
});
