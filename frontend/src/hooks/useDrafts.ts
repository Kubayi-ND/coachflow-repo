import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { AiDraft } from "@/types";

const DRAFTS_KEY = ["drafts", "pending"] as const;

/** The Approvals inbox feed. Query key is invalidated by useApproveDraft and
 * useRejectDraft below so the inbox count updates without a manual refresh
 * (frontend/CLAUDE.md "API integration pattern"). */
export function useDrafts() {
  return useQuery({
    queryKey: DRAFTS_KEY,
    queryFn: () => apiFetch<AiDraft[]>("/api/drafts?status=pending"),
  });
}

export function useApproveDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ draftId, editedBody }: { draftId: string; editedBody?: string }) =>
      apiFetch<AiDraft>(`/api/drafts/${draftId}/approve`, {
        method: "POST",
        body: JSON.stringify({ edited_body: editedBody ?? null }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: DRAFTS_KEY }),
  });
}

export function useRejectDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ draftId, reason }: { draftId: string; reason: string }) =>
      apiFetch<AiDraft>(`/api/drafts/${draftId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: DRAFTS_KEY }),
  });
}
