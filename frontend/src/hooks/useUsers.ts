import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { AppUser, UserRole } from "@/types";

const USERS_KEY = ["admin", "users"] as const;

/** GET /api/admin/users — excludes soft-deleted users server-side, so this
 * list never needs to filter or render a "deleted" state. */
export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: () => apiFetch<AppUser[]>("/api/admin/users"),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: UserRole }) =>
      apiFetch<AppUser>("/api/admin/users", { method: "POST", body: JSON.stringify({ email, role }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useSuspendUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => apiFetch<AppUser>(`/api/admin/users/${userId}/suspend`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useReactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => apiFetch<AppUser>(`/api/admin/users/${userId}/reactivate`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => apiFetch<void>(`/api/admin/users/${userId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}
