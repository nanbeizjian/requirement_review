import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { SessionProvider, useSession } from "./session/SessionContext";
import { SessionForm } from "./session/SessionForm";
import { AppShell } from "./shell/AppShell";
import { GlobalAlertsProvider } from "./shell/GlobalAlerts";

function SessionGate() {
  const { actor, setSession } = useSession();
  if (!actor) return <SessionForm onSubmit={setSession} />;
  return <Outlet />;
}

export default function App() {
  return (
    <SessionProvider>
      <GlobalAlertsProvider>
        <Routes>
          <Route element={<SessionGate />}>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/reviews" replace />} />
              <Route path="/reviews" element={<div data-testid="placeholder-list">评审列表占位</div>} />
              <Route path="*" element={<div>404</div>} />
            </Route>
          </Route>
        </Routes>
      </GlobalAlertsProvider>
    </SessionProvider>
  );
}
