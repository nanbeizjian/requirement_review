import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./Select";

it("renders options and fires onChange", async () => {
  const onChange = vi.fn();
  render(<Select id="r" label="Role" value="reviewer" onChange={onChange} options={[{ value: "reviewer", label: "reviewer" }, { value: "viewer", label: "viewer" }]} />);
  await userEvent.selectOptions(screen.getByLabelText("Role"), "viewer");
  expect(onChange).toHaveBeenCalledWith("viewer");
});
