import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { UserRole } from "@/types";
import { useSession } from "./useSession";

interface CurrentUser {
  id: string;
  email: string;
  role: UserRole;
  mustResetPassword: boolean;
  assignedClientIds: string[];
}

/** Backed by GET /api/users/me (add the route if it doesn't exist yet) —
 * the frontend never derives role from the JWT payload itself, since the
 * backend is the single source of truth for role/tenant authorization
 * (root CLAUDE.md "Roles"). */
export function useRole() {
  const { isAuthenticated } = useSession();

  const query = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiFetch<CurrentUser>("/api/users/me"),
    enabled: isAuthenticated,
  });

  return {
    user: query.data,
    isAdmin: query.data?.role === "admin",
    mustResetPassword: query.data?.mustResetPassword ?? false,
    isLoading: query.isLoading,
  };
}
