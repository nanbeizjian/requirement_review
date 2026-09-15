import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Textarea } from "./Textarea";

function Stateful({ id, label, maxLength }: { id: string; label: string; maxLength?: number }) {
  const [v, setV] = useState("");
  return <Textarea id={id} label={label} value={v} onChange={setV} maxLength={maxLength} />;
}

it("forwards value and respects maxLength", async () => {
  render(<Stateful id="t" label="意见" maxLength={5} />);
  const el = screen.getByLabelText("意见");
  await userEvent.type(el, "abcdef");
  expect(el).toHaveValue("abcde");
});
