import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { ImportItem, ImportJob, ImportSource, TenantId } from "@/types";

function jobsKey(tenantId?: TenantId) {
  return ["admin", "imports", tenantId ?? "all"] as const;
}

/** Polls while any job in the list is still running, so the Admin > Import
 * page's progress counts update without a manual refresh — the one-time
 * backfill can take a while for a folder full of PDFs/transcripts. */
export function useImportJobs(tenantId?: TenantId) {
  return useQuery({
    queryKey: jobsKey(tenantId),
    queryFn: () => apiFetch<ImportJob[]>(`/api/admin/imports${tenantId ? `?tenant_id=${tenantId}` : ""}`),
    refetchInterval: (query) => (query.state.data?.some((job) => job.status === "running") ? 3000 : false),
  });
}

export function useStartImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tenantId, source, folderId }: { tenantId: TenantId; source: ImportSource; folderId: string }) =>
      apiFetch<ImportJob>("/api/admin/imports", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tenantId, source, folder_id: folderId }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "imports"] }),
  });
}

export function useImportJobItems(jobId: string | null) {
  return useQuery({
    queryKey: ["admin", "imports", "items", jobId],
    queryFn: () => apiFetch<ImportItem[]>(`/api/admin/imports/${jobId}/items`),
    enabled: jobId !== null,
  });
}

/** Powers the unmatched-items panel's one-click "assign client" action —
 * same shape as useResolveUnmatchedEvent for the Calendar view's unmatched
 * calendar events. */
export function useResolveImportItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, clientId }: { itemId: string; clientId: string }) =>
      apiFetch<ImportItem>(`/api/admin/imports/items/${itemId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ client_id: clientId }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "imports"] }),
  });
}
