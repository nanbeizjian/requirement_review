import { render, screen } from "@testing-library/react";
import { Spinner } from "./Spinner";

it("has role=status and accessible label", () => {
  render(<Spinner label="加载中" />);
  expect(screen.getByRole("status")).toHaveTextContent("加载中");
});
