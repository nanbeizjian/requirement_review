import type { ReactNode } from "react";
import { SessionProvider } from "../../session/SessionContext";
import { ReviewsRefreshProvider } from "../reviews/ReviewsRefreshContext";

export function TestWrap(props: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ReviewsRefreshProvider>{props.children}</ReviewsRefreshProvider>
    </SessionProvider>
  );
}
