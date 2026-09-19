import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch } from "@/lib/apiClient";
import type { Scorecard } from "@/types";

/** A session's post-session ICF critique, or null when none has been
 * generated yet (the API answers 404). */
export function useScorecard(sessionId: string | null | undefined) {
  return useQuery({
    queryKey: ["scorecard", sessionId],
    queryFn: async () => {
      try {
        return await apiFetch<Scorecard>(`/api/scorecards/${sessionId}`);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    enabled: !!sessionId,
  });
}

/** Runs (or, with refresh, re-runs) the ICF critique for a session. The
 * first run also creates the client summary as a pending Approvals draft,
 * so the drafts feed is refreshed too. */
export function useRunAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, refresh = false }: { sessionId: string; refresh?: boolean }) =>
      apiFetch<Scorecard>(`/api/sessions/${sessionId}/analysis?refresh=${refresh}`, { method: "POST" }),
    onSuccess: (scorecard, { sessionId }) => {
      queryClient.setQueryData(["scorecard", sessionId], scorecard);
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });
}

/** The API's error body is FastAPI's {"detail": "..."}; show just the message. */
export function analysisErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: unknown };
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      // not JSON — fall through
    }
  }
  return "The analysis couldn't be run. Please try again.";
}
