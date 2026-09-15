import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Role } from "../api/types";

export interface Session {
  userId: string;
  projectId: string;
  role: Role;
}

export interface SessionContextValue {
  session: Session | null;
  setSession: (next: Session | null) => void;
  requireSession: () => Session;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

const STORAGE_KEY = "requirement-review.session.v1";

function readStoredSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    if (
      typeof parsed.userId === "string" &&
      typeof parsed.projectId === "string" &&
      (parsed.role === "admin" || parsed.role === "reviewer" || parsed.role === "viewer")
    ) {
      return { userId: parsed.userId, projectId: parsed.projectId, role: parsed.role };
    }
    return null;
  } catch {
    return null;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(() => readStoredSession());

  const setSession = useCallback((next: Session | null) => {
    setSessionState(next);
    if (typeof window === "undefined") return;
    if (next === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  }, []);

  const requireSession = useCallback((): Session => {
    if (!session) {
      throw new Error("active session required");
    }
    return session;
  }, [session]);

  const value = useMemo(
    () => ({ session, setSession, requireSession }),
    [session, setSession, requireSession]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return ctx;
}
