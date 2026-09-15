import type { ReactNode } from "react";
import { useSession } from "../session/SessionContext";
import type { Role } from "../api/types";

interface Props {
  allow: readonly Role[];
  fallback?: ReactNode;
  children: ReactNode;
}

export function RoleGate({ allow, fallback = null, children }: Props) {
  const { actor } = useSession();
  if (!actor) return <>{fallback}</>;
  return allow.includes(actor.role) ? <>{children}</> : <>{fallback}</>;
}
