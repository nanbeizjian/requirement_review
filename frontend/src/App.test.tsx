import { render, screen } from "@testing-library/react";
import App from "./App";

it("renders the bootstrap placeholder", () => {
  render(<App />);
  expect(screen.getByText(/workbench bootstrapping/i)).toBeInTheDocument();
});
