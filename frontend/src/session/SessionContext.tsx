import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Actor as ApiActor } from "../api/client";
import { clearSession, readSession, writeSession, type Session } from "./storage";

export interface SessionContextValue {
  actor: ApiActor | null;
  setSession: (s: Session) => void;
  reset: () => void;
}

const Ctx = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(() => readSession());

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "rr:session:v1") setSessionState(readSession());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setSession = useCallback((s: Session) => {
    writeSession(s);
    setSessionState(s);
  }, []);

  const reset = useCallback(() => {
    clearSession();
    setSessionState(null);
  }, []);

  const value = useMemo<SessionContextValue>(() => ({
    actor: session ? { userId: session.userId, projectId: session.projectId, role: session.role } : null,
    setSession,
    reset,
  }), [session, setSession, reset]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession(): SessionContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used within SessionProvider");
  return v;
}
