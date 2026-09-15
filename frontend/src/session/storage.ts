import type { Role } from "../api/types";

export interface Session {
  userId: string;
  projectId: string;
  role: Role;
}

export const SESSION_STORAGE_KEY = "rr:session:v1";

const VALID_ROLES = new Set<Role>(["admin", "reviewer", "viewer"]);

function isSession(v: unknown): v is Session {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.userId === "string" && o.userId.length > 0 &&
    typeof o.projectId === "string" && o.projectId.length > 0 &&
    typeof o.role === "string" && VALID_ROLES.has(o.role as Role)
  );
}

export function readSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return isSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeSession(s: Session): void {
  sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(s));
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}
