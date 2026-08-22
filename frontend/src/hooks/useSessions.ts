import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { Session, SessionPrep, SessionTypeId, UnmatchedEvent } from "@/types";

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => apiFetch<Session[]>("/api/sessions"),
  });
}

export function useSessionPrep(sessionId: string | null) {
  return useQuery({
    queryKey: ["session-prep", sessionId],
    queryFn: () => apiFetch<SessionPrep>(`/api/sessions/${sessionId}/prep`),
    enabled: !!sessionId,
  });
}

const UNMATCHED_KEY = ["sessions", "unmatched-events"] as const;

export function useUnmatchedEvents() {
  return useQuery({
    queryKey: UNMATCHED_KEY,
    queryFn: () => apiFetch<UnmatchedEvent[]>("/api/sessions/unmatched-events"),
  });
}

/** Powers the Calendar view's one-click "assign session type" action on an
 * unmatched event (frontend/CLAUDE.md: "so the coach isn't blocked"). */
export function useResolveUnmatchedEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ eventId, sessionType }: { eventId: string; sessionType: SessionTypeId }) =>
      apiFetch<UnmatchedEvent>(`/api/sessions/unmatched-events/${eventId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ resolved_session_type: sessionType }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: UNMATCHED_KEY }),
  });
}
