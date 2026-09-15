import { render, screen } from "@testing-library/react";
import { Alert } from "./Alert";

it("renders severity text and correlation id", () => {
  render(<Alert severity="error" message="conflict" correlationId="abc-123" />);
  expect(screen.getByRole("alert")).toHaveTextContent("conflict");
  expect(screen.getByRole("alert")).toHaveTextContent("abc-123");
});
