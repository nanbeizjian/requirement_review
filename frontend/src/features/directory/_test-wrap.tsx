import type { ReactNode } from "react";
import { SessionProvider } from "../../session/SessionContext";

export function TestWrap(props: { children: ReactNode }) {
  return <SessionProvider>{props.children}</SessionProvider>;
}
