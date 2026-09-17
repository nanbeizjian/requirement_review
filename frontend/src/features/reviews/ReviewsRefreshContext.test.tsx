import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ReviewsRefreshProvider, useReviewsRefresher } from "./ReviewsRefreshContext";

afterEach(() => {
  sessionStorage.clear();
});

describe("ReviewsRefreshContext", () => {
  it("starts with refreshCounter = 0", () => {
    const { result } = renderHook(() => useReviewsRefresher(), { wrapper: ReviewsRefreshProvider });
    expect(result.current.refreshCounter).toBe(0);
    expect(typeof result.current.requestRefresh).toBe("function");
  });

  it("coalesces multiple requestRefresh invocations in the same tick to one increment", async () => {
    const { result } = renderHook(() => useReviewsRefresher(), { wrapper: ReviewsRefreshProvider });
    const before = result.current.refreshCounter;
    await act(async () => {
      result.current.requestRefresh();
      result.current.requestRefresh();
      result.current.requestRefresh();
    });
    expect(result.current.refreshCounter).toBe(before + 1);
  });

  it("increments refreshCounter for cross-tick requests", async () => {
    const { result } = renderHook(() => useReviewsRefresher(), { wrapper: ReviewsRefreshProvider });
    const before = result.current.refreshCounter;
    await act(async () => {
      result.current.requestRefresh();
    });
    expect(result.current.refreshCounter).toBe(before + 1);
    await act(async () => {
      result.current.requestRefresh();
    });
    expect(result.current.refreshCounter).toBe(before + 2);
  });

  it("throws when useReviewsRefresher is consumed without a Provider", () => {
    expect(() => renderHook(() => useReviewsRefresher())).toThrow(/ReviewsRefreshProvider/);
  });

  it("shares the counter between sibling consumers of the same provider", async () => {
    function Counter() {
      const { refreshCounter } = useReviewsRefresher();
      return <span data-testid="counter">{refreshCounter}</span>;
    }
    function Button() {
      const { requestRefresh } = useReviewsRefresher();
      return <button onClick={() => requestRefresh()}>bump</button>;
    }
    render(
      <ReviewsRefreshProvider>
        <Counter />
        <Button />
      </ReviewsRefreshProvider>,
    );
    expect(screen.getByTestId("counter")).toHaveTextContent("0");
    await userEvent.click(screen.getByRole("button", { name: /bump/ }));
    expect(screen.getByTestId("counter")).toHaveTextContent("1");
    await userEvent.click(screen.getByRole("button", { name: /bump/ }));
    expect(screen.getByTestId("counter")).toHaveTextContent("2");
  });
});
