import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert/Alert";

export interface GlobalAlert {
  id: number;
  severity: "info" | "warn" | "error" | "success";
  message: string;
  correlationId?: string;
}

interface Ctx {
  alerts: GlobalAlert[];
  push: (a: Omit<GlobalAlert, "id">) => void;
  dismiss: (id: number) => void;
}

const GlobalAlertsCtx = createContext<Ctx | null>(null);

export function GlobalAlertsProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<GlobalAlert[]>([]);
  const push = useCallback((a: Omit<GlobalAlert, "id">) => {
    const id = Date.now() + Math.random();
    setAlerts((s) => [...s, { ...a, id }]);
  }, []);
  const dismiss = useCallback((id: number) => setAlerts((s) => s.filter((a) => a.id !== id)), []);
  const value = useMemo<Ctx>(() => ({ alerts, push, dismiss }), [alerts, push, dismiss]);
  return (
    <GlobalAlertsCtx.Provider value={value}>
      {children}
      <div aria-live="polite">
        {alerts.map((a) => (
          <Alert key={a.id} severity={a.severity} message={a.message} {...(a.correlationId ? { correlationId: a.correlationId } : {})} />
        ))}
      </div>
    </GlobalAlertsCtx.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useGlobalAlerts(): Ctx {
  const v = useContext(GlobalAlertsCtx);
  if (!v) throw new Error("GlobalAlertsProvider missing");
  return v;
}
