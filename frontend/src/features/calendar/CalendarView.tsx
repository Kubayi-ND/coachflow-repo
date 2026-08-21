import { differenceInCalendarDays } from "date-fns";

import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useClients } from "@/hooks/useClients";
import { useResolveUnmatchedEvent, useSessions, useUnmatchedEvents } from "@/hooks/useSessions";
import { workingDaysUntil } from "@/lib/workingDays";
import { SESSION_TYPES, SESSION_TYPE_IDS } from "@/types";
import type { Session, SessionStatus } from "@/types";

const STATUS_TONE: Record<SessionStatus, "neutral" | "teal" | "amber"> = {
  upcoming: "neutral",
  prep_generating: "amber",
  ready_for_review: "teal",
  sent: "neutral",
};

const STATUS_LABEL: Record<SessionStatus, string> = {
  upcoming: "Upcoming",
  prep_generating: "Prep generating",
  ready_for_review: "Ready for review",
  sent: "Sent",
};

/** Every upcoming session across both tenants, grouped by client, with a
 * countdown against that session type's lead time (frontend/CLAUDE.md). */
export function CalendarView() {
  const { data: clients } = useClients();
  const { data: sessions, isLoading } = useSessions();
  const { data: unmatchedEvents } = useUnmatchedEvents();
  const resolveEvent = useResolveUnmatchedEvent();

  const clientsById = new Map((clients ?? []).map((c) => [c.id, c]));
  const sessionsByClient = groupByClient(sessions ?? []);

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl mb-4">Calendar</h1>
        {isLoading && <CalendarSkeleton />}
        <div className="space-y-6">
          {[...sessionsByClient.entries()].map(([clientId, clientSessions]) => (
            <div key={clientId}>
              <h2 className="text-sm font-medium text-slate mb-2">
                {clientsById.get(clientId)?.name ?? "Unknown client"}
              </h2>
              <ul className="space-y-2">
                {clientSessions.map((session) => (
                  <li
                    key={session.id}
                    className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm">{SESSION_TYPES[session.type].label}</p>
                      <p className="text-xs text-slate tabular-nums">
                        {differenceInCalendarDays(new Date(session.eventDate), new Date())} days to event ·{" "}
                        {workingDaysUntil(new Date(session.triggerDate))} working days to trigger
                      </p>
                    </div>
                    <Pill tone={STATUS_TONE[session.status]}>{STATUS_LABEL[session.status]}</Pill>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {unmatchedEvents && unmatchedEvents.length > 0 && (
        <section>
          <h2 className="text-lg mb-2">Unmatched events</h2>
          <p className="text-sm text-slate mb-3">
            Calendar events that didn't match one of the five session-naming conventions. Assign a type so this
            client isn't blocked.
          </p>
          <ul className="space-y-2">
            {unmatchedEvents.map((event) => (
              <li
                key={event.id}
                className="flex items-center justify-between rounded-md border border-amber/40 bg-amber/5 px-4 py-3"
              >
                <span className="text-sm">{event.rawEventSummary}</span>
                <select
                  className="text-sm rounded-md border border-slate/30 bg-transparent px-2 py-1"
                  defaultValue=""
                  onChange={(e) =>
                    e.target.value &&
                    resolveEvent.mutate({ eventId: event.id, sessionType: e.target.value as never })
                  }
                >
                  <option value="" disabled>
                    Assign session type
                  </option>
                  {SESSION_TYPE_IDS.map((id) => (
                    <option key={id} value={id}>
                      {SESSION_TYPES[id].label}
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function CalendarSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 2 }).map((_, groupIndex) => (
        <div key={groupIndex}>
          <Skeleton className="h-4 w-32 mb-2" />
          <ul className="space-y-2">
            {Array.from({ length: 2 }).map((_, rowIndex) => (
              <li
                key={rowIndex}
                className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3"
              >
                <div className="space-y-2">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-56" />
                </div>
                <Skeleton className="h-5 w-24 rounded-full" />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function groupByClient(sessions: Session[]): Map<string, Session[]> {
  const grouped = new Map<string, Session[]>();
  for (const session of sessions) {
    const existing = grouped.get(session.clientId) ?? [];
    existing.push(session);
    grouped.set(session.clientId, existing);
  }
  return grouped;
}
