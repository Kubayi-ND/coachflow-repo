import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { PromptTemplate, SessionTypeId } from "@/types";

const TEMPLATES_KEY = ["admin", "prompt-templates"] as const;

/** Current (latest-version) prompt templates — the same rows
 * draft_generator.py / scorecard_generator.py read at generation time, so an
 * edit here changes what the AI actually sends to Gemini. */
export function usePromptTemplates() {
  return useQuery({
    queryKey: TEMPLATES_KEY,
    queryFn: () => apiFetch<PromptTemplate[]>("/api/admin/prompt-templates"),
  });
}

export function usePromptTemplateHistory(entryGroupId: string | null) {
  return useQuery({
    queryKey: ["admin", "prompt-templates", "history", entryGroupId],
    queryFn: () => apiFetch<PromptTemplate[]>(`/api/admin/prompt-templates/${entryGroupId}/history`),
    enabled: entryGroupId !== null,
  });
}

export function useCreatePromptTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionType,
      phase,
      title,
      body,
    }: {
      sessionType: SessionTypeId;
      phase: "pre" | "post";
      title: string;
      body: string;
    }) =>
      apiFetch<PromptTemplate>("/api/admin/prompt-templates", {
        method: "POST",
        body: JSON.stringify({ session_type: sessionType, phase, title, body }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}

export function usePostPromptTemplateVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entryGroupId, title, body }: { entryGroupId: string; title: string; body: string }) =>
      apiFetch<PromptTemplate>(`/api/admin/prompt-templates/${entryGroupId}/versions`, {
        method: "POST",
        body: JSON.stringify({ title, body }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}
