import { differenceInCalendarDays } from "date-fns";
import { useEffect, useState } from "react";

import { Pill } from "@/components/ui/Pill";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useClients } from "@/hooks/useClients";
import { useResolveUnmatchedEvent, useSessionPrep, useSessions, useUnmatchedEvents } from "@/hooks/useSessions";
import { workingDaysUntil } from "@/lib/workingDays";
import { SESSION_TYPES, SESSION_TYPE_IDS } from "@/types";
import type { Session, SessionPrep, SessionStatus } from "@/types";

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

type PrepTab = "prep" | "review" | "history";

export function CalendarView() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [activeTab, setActiveTab] = useState<PrepTab>("prep");
  const { data: clients } = useClients();
  const { data: sessions, isLoading } = useSessions();
  const { data: unmatchedEvents } = useUnmatchedEvents();
  const resolveEvent = useResolveUnmatchedEvent();
  const prepQuery = useSessionPrep(selectedSession?.id ?? null);
  const clientsById = new Map((clients ?? []).map((client) => [client.id, client]));
  const sessionsByClient = groupByClient(sessions ?? []);

  return (
    <div className="space-y-8">
      <section>
        <h1 className="mb-4 text-2xl">Upcoming sessions</h1>
        <QuickStats clients={clients ?? []} sessions={sessions ?? []} unmatchedCount={unmatchedEvents?.length ?? 0} />
        {isLoading && <CalendarSkeleton />}
        <div className="space-y-6">
          {[...sessionsByClient.entries()].map(([clientId, clientSessions]) => (
            <div key={clientId}>
              <h2 className="mb-2 text-sm font-medium text-slate">{clientsById.get(clientId)?.name ?? "Unknown client"}</h2>
              <ul className="space-y-2">
                {clientSessions.map((session) => (
                  <li key={session.id} className="rounded-md border border-slate/15">
                    <button
                      type="button"
                      className="flex w-full items-center justify-between px-4 py-3 text-left hover:border-teal/50"
                      onClick={() => {
                        setSelectedSession(session);
                        setActiveTab("prep");
                      }}
                    >
                      <div>
                        <p className="text-sm">{SESSION_TYPES[session.type].label}</p>
                        <p className="text-xs text-slate tabular-nums">
                          {differenceInCalendarDays(new Date(session.eventDate), new Date())} days to event · {workingDaysUntil(new Date(session.triggerDate))} working days to trigger
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Pill tone={STATUS_TONE[session.status]}>{STATUS_LABEL[session.status]}</Pill>
                        <span className="text-xs font-medium text-teal">View prep</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {unmatchedEvents && unmatchedEvents.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg">Unmatched events</h2>
          <p className="mb-3 text-sm text-slate">Calendar events that didn&apos;t match one of the five session-naming conventions. Assign a type so this client isn&apos;t blocked.</p>
          <ul className="space-y-2">
            {unmatchedEvents.map((event) => (
              <li key={event.id} className="flex items-center justify-between rounded-md border border-amber/40 bg-amber/5 px-4 py-3">
                <span className="text-sm">{event.rawEventSummary}</span>
                <Select className="text-sm" defaultValue="" onChange={(e) => e.target.value && resolveEvent.mutate({ eventId: event.id, sessionType: e.target.value as never })}>
                  <option value="" disabled>Assign session type</option>
                  {SESSION_TYPE_IDS.map((id) => <option key={id} value={id}>{SESSION_TYPES[id].label}</option>)}
                </Select>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selectedSession && (
        <SessionPrepDrawer
          session={selectedSession}
          data={prepQuery.data}
          isLoading={prepQuery.isLoading}
          error={prepQuery.error}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}

function QuickStats({
  clients,
  sessions,
  unmatchedCount,
}: {
  clients: { id: string }[];
  sessions: Session[];
  unmatchedCount: number;
}) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const upcomingCount = sessions.filter((session) => new Date(session.eventDate) >= today).length;
  const readyCount = sessions.filter((session) => session.status === "ready_for_review").length;
  const attentionCount = unmatchedCount + sessions.filter((session) => session.status === "prep_generating").length;
  const stats = [
    { label: "Active clients", value: clients.length },
    { label: "Upcoming sessions", value: upcomingCount },
    { label: "Prep ready", value: readyCount, tone: "text-teal" },
    { label: "Need attention", value: attentionCount, tone: attentionCount > 0 ? "text-amber" : undefined },
  ];

  return (
    <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-md border border-slate/15 px-4 py-3">
          <p className={`text-2xl tabular-nums ${stat.tone ?? ""}`}>{stat.value}</p>
          <p className="mt-1 text-xs text-slate">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}

function SessionPrepDrawer({ session, data, isLoading, error, activeTab, onTabChange, onClose }: {
  session: Session;
  data: SessionPrep | undefined;
  isLoading: boolean;
  error: Error | null;
  activeTab: PrepTab;
  onTabChange: (tab: PrepTab) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-20 bg-ink/30" role="presentation" onClick={onClose}>
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col overflow-hidden bg-paper shadow-xl" role="dialog" aria-modal="true" aria-labelledby="session-prep-title" onClick={(event) => event.stopPropagation()}>
        <header className="border-b border-slate/20 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate">{SESSION_TYPES[session.type].label}</p>
              <h2 id="session-prep-title" className="mt-1 text-xl">Session preparation</h2>
              <p className="mt-1 text-sm text-slate">Generated from this client&apos;s current context and prior sessions.</p>
            </div>
            <button type="button" className="text-2xl leading-none text-slate transition-colors hover:text-ink" aria-label="Close" onClick={onClose}>×</button>
          </div>
          <div className="mt-4 flex gap-4 border-b border-slate/15">
            {(["prep", "review", "history"] as const).map((tab) => (
              <button key={tab} type="button" className={`border-b-2 px-1 pb-2 text-sm ${activeTab === tab ? "border-teal text-teal" : "border-transparent text-slate"}`} onClick={() => onTabChange(tab)}>
                {tab === "prep" ? "Session prep" : tab === "review" ? "Last review" : "History"}
              </button>
            ))}
          </div>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {isLoading && <p className="text-sm text-slate">Building prep from the Context Library and prior sessions...</p>}
          {error && <p className="text-sm text-amber">Unable to load this session&apos;s preparation.</p>}
          {!isLoading && !error && data && activeTab === "prep" && <pre className="whitespace-pre-wrap font-body text-sm leading-6 text-ink">{data.prep}</pre>}
          {!isLoading && !error && data && activeTab === "review" && (data.scorecard ? <pre className="whitespace-pre-wrap font-body text-sm leading-6 text-ink">{JSON.stringify(data.scorecard, null, 2)}</pre> : <p className="text-sm text-slate">No completed review is available for this session yet.</p>)}
          {!isLoading && !error && data && activeTab === "history" && (data.history.length > 0 ? <ul className="space-y-4">{data.history.map((item) => <li key={item.id} className="border-b border-slate/15 pb-4"><p className="text-xs text-slate tabular-nums">{new Date(item.eventDate).toLocaleDateString()}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-6">{item.summary ?? "No sent summary is available."}</p></li>)}</ul> : <p className="text-sm text-slate">No prior sessions of this type are on file.</p>)}
        </div>
      </aside>
    </div>
  );
}

function CalendarSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 2 }).map((_, groupIndex) => (
        <div key={groupIndex}>
          <Skeleton className="mb-2 h-4 w-32" />
          <ul className="space-y-2">
            {Array.from({ length: 2 }).map((_, rowIndex) => (
              <li key={rowIndex} className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3">
                <div className="space-y-2"><Skeleton className="h-4 w-40" /><Skeleton className="h-3 w-56" /></div>
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
  for (const session of sessions) grouped.set(session.clientId, [...(grouped.get(session.clientId) ?? []), session]);
  return grouped;
}
