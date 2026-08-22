import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { ContextLibraryEntry } from "@/types";

function entriesKey(clientId?: string) {
  return ["admin", "context-library", clientId ?? "all"] as const;
}

/** Current (latest-version) Context Library entries, optionally scoped to a
 * client (org-wide entries are always included alongside them — matches
 * context_builder.py's own read filter). */
export function useContextLibraryEntries(clientId?: string) {
  return useQuery({
    queryKey: entriesKey(clientId),
    queryFn: () =>
      apiFetch<ContextLibraryEntry[]>(`/api/admin/context-library${clientId ? `?client_id=${clientId}` : ""}`),
  });
}

export function useContextLibraryHistory(entryGroupId: string | null) {
  return useQuery({
    queryKey: ["admin", "context-library", "history", entryGroupId],
    queryFn: () => apiFetch<ContextLibraryEntry[]>(`/api/admin/context-library/${entryGroupId}/history`),
    enabled: entryGroupId !== null,
  });
}

export function useCreateContextLibraryEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ clientId, title, body }: { clientId: string | null; title: string; body: string }) =>
      apiFetch<ContextLibraryEntry>("/api/admin/context-library", {
        method: "POST",
        body: JSON.stringify({ client_id: clientId, title, body }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "context-library"] }),
  });
}

export function usePostContextLibraryVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entryGroupId, title, body }: { entryGroupId: string; title: string; body: string }) =>
      apiFetch<ContextLibraryEntry>(`/api/admin/context-library/${entryGroupId}/versions`, {
        method: "POST",
        body: JSON.stringify({ title, body }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "context-library"] }),
  });
}
