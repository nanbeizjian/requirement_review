import { useState, type Dispatch, type SetStateAction } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormField } from "./FormField";

function Stateful({ id, label, required, error }: { id: string; label: string; required?: boolean; error?: string }) {
  const [v, setV] = useState("");
  const onChange: Dispatch<SetStateAction<string>> = setV;
  const extra = {
    ...(required !== undefined ? { required } : {}),
    ...(error !== undefined ? { error } : {}),
  };
  return <FormField id={id} label={label} value={v} onChange={onChange} {...extra} />;
}

it("labels the input and echoes value changes", async () => {
  render(<Stateful id="u" label="User" />);
  const input = screen.getByLabelText("User");
  await userEvent.type(input, "abc");
  expect(input).toHaveValue("abc");
});

it("marks required and reports aria-invalid when error provided", () => {
  render(<Stateful id="u" label="User" required error="必填" />);
  const input = screen.getByLabelText("User *");
  expect(input).toBeRequired();
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("alert")).toHaveTextContent("必填");
});
