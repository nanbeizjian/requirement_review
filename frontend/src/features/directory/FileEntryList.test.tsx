import { render, screen } from "@testing-library/react";
import { FileEntryList } from "./FileEntryList";
import type { SubmissionItem } from "./useDirectorySubmission";

it("renders per-file status rows with safe errors", () => {
  const items: SubmissionItem[] = [
    { id: 1, name: "a.md", status: "submitted", reviewId: "r1", text: "" },
    { id: 2, name: "b.md", status: "failed", errorMessage: "bad", correlationId: "cid-9", text: "" },
  ];
  render(<FileEntryList items={items} onRetry={() => {}} />);
  expect(screen.getByText(/a\.md/)).toBeInTheDocument();
  expect(screen.getByText(/bad/)).toBeInTheDocument();
  expect(screen.getByText(/cid-9/)).toBeInTheDocument();
});
