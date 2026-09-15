import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionForm } from "./SessionForm";

it("calls onSubmit with a normalized session", async () => {
  const onSubmit = vi.fn();
  sessionStorage.clear();
  render(<SessionForm onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText(/用户 ID/), "u1");
  await userEvent.type(screen.getByLabelText(/项目 ID/), "p1");
  await userEvent.selectOptions(screen.getByLabelText(/角色/), "reviewer");
  await userEvent.click(screen.getByRole("button", { name: /开始/ }));
  expect(onSubmit).toHaveBeenCalledWith({ userId: "u1", projectId: "p1", role: "reviewer" });
});
