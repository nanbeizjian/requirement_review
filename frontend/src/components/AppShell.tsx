import { useState, type ReactNode } from "react";
import { useSession } from "../session/SessionContext";

export default function AppShell({ nav, children }: { nav: ReactNode; children: ReactNode }) {
  const { session, setSession } = useSession();
  const [userId, setUserId] = useState(session?.userId ?? "");
  const [projectId, setProjectId] = useState(session?.projectId ?? "");
  const [role, setRole] = useState(session?.role ?? "viewer");

  const apply = () => {
    if (!userId.trim() || !projectId.trim()) return;
    setSession({ userId: userId.trim(), projectId: projectId.trim(), role });
  };

  const clear = () => setSession(null);

  return (
    <div className="app-shell">
      <header className="app-header">
        {nav}
        <div className="session" aria-label="Session controls">
          <input
            aria-label="User ID"
            placeholder="user id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ width: 120 }}
          />
          <input
            aria-label="Project ID"
            placeholder="project id"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            style={{ width: 160 }}
          />
          <select
            aria-label="Role"
            value={role}
            onChange={(e) => setRole(e.target.value as typeof role)}
          >
            <option value="admin">admin</option>
            <option value="reviewer">reviewer</option>
            <option value="viewer">viewer</option>
          </select>
          <button type="button" onClick={apply}>Apply</button>
          {session && (
            <button type="button" onClick={clear} aria-label="Clear session">
              Clear
            </button>
          )}
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
