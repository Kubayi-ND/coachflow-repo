import { differenceInCalendarDays } from "date-fns";
import { useEffect, useState } from "react";

import { CountdownChip } from "@/components/ui/CountdownChip";
import { Pill } from "@/components/ui/Pill";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatTile } from "@/components/ui/StatTile";
import { AlertTriangleIcon, CalendarIcon, ChevronRightIcon, CheckCircleIcon, UsersIcon, XIcon } from "@/components/ui/icons";
import { useClients } from "@/hooks/useClients";
import { useResolveUnmatchedEvent, useSessionPrep, useSessions, useUnmatchedEvents } from "@/hooks/useSessions";
import { workingDaysUntil } from "@/lib/workingDays";
import { SESSION_TYPES, SESSION_TYPE_IDS } from "@/types";
import type { Session, SessionPrep, SessionStatus, TenantId } from "@/types";

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
        <QuickStats clients={clients ?? []} sessions={sessions ?? []} unmatchedCount={unmatchedEvents?.length ?? 0} />

        {isLoading && <CalendarSkeleton />}

        <div className="space-y-6">
          {[...sessionsByClient.entries()].map(([clientId, clientSessions]) => {
            const client = clientsById.get(clientId);
            return (
              <div key={clientId}>
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-ink">{client?.name ?? "Unknown client"}</h2>
                    {client && <Pill>{client.tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>}
                  </div>
                  <span className="text-xs text-slate tabular-nums">
                    {clientSessions.length} session{clientSessions.length === 1 ? "" : "s"}
                  </span>
                </div>
                <ul className="space-y-2">
                  {clientSessions.map((session) => (
                    <li key={session.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4 text-left shadow-card transition-all duration-150 hover:border-teal/30 hover:shadow-cardmd"
                        onClick={() => {
                          setSelectedSession(session);
                          setActiveTab("prep");
                        }}
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-ink">{SESSION_TYPES[session.type].label}</p>
                          <p className="mt-1 text-xs tabular-nums text-slate">
                            {differenceInCalendarDays(new Date(session.eventDate), new Date())} calendar days to event
                          </p>
                        </div>
                        <div className="flex flex-shrink-0 items-center gap-3">
                          <Pill tone={STATUS_TONE[session.status]}>{STATUS_LABEL[session.status]}</Pill>
                          <CountdownChip workingDaysLeft={workingDaysUntil(new Date(session.triggerDate))} />
                          <span className="hidden items-center gap-1 text-xs font-medium text-teal sm:flex">
                            View prep
                            <ChevronRightIcon className="h-3.5 w-3.5" />
                          </span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </section>

      {unmatchedEvents && unmatchedEvents.length > 0 && (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangleIcon className="h-4 w-4 text-amber" />
            <h2 className="text-sm font-semibold text-amber">Unmatched events</h2>
            <span className="tabular-nums text-xs text-amber/80">({unmatchedEvents.length})</span>
          </div>
          <p className="mb-3 text-sm text-slate">
            Calendar events that didn&apos;t match one of the five session-naming conventions. Assign a type so this
            client isn&apos;t blocked.
          </p>
          <ul className="space-y-2">
            {unmatchedEvents.map((event) => (
              <li
                key={event.id}
                className="flex items-center justify-between gap-4 rounded-xl border border-amber/30 bg-amber/5 px-4 py-3"
              >
                <span className="min-w-0 flex-1 truncate text-sm text-ink">{event.rawEventSummary}</span>
                <Select
                  className="flex-shrink-0 text-sm"
                  defaultValue=""
                  onChange={(e) => e.target.value && resolveEvent.mutate({ eventId: event.id, sessionType: e.target.value as never })}
                >
                  <option value="" disabled>
                    Assign session type
                  </option>
                  {SESSION_TYPE_IDS.map((id) => (
                    <option key={id} value={id}>
                      {SESSION_TYPES[id].label}
                    </option>
                  ))}
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
  clients: { id: string; tenantId: TenantId }[];
  sessions: Session[];
  unmatchedCount: number;
}) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const upcomingCount = sessions.filter((session) => new Date(session.eventDate) >= today).length;
  const readyCount = sessions.filter((session) => session.status === "ready_for_review").length;
  const attentionCount = unmatchedCount + sessions.filter((session) => session.status === "prep_generating").length;

  return (
    <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatTile label="Active clients" value={clients.length} icon={<UsersIcon className="h-5 w-5" />} tone="neutral" />
      <StatTile label="Upcoming sessions" value={upcomingCount} icon={<CalendarIcon className="h-5 w-5" />} tone="neutral" />
      <StatTile label="Prep ready" value={readyCount} icon={<CheckCircleIcon className="h-5 w-5" />} tone="teal" />
      <StatTile
        label="Need attention"
        value={attentionCount}
        icon={<AlertTriangleIcon className="h-5 w-5" />}
        tone={attentionCount > 0 ? "amber" : "neutral"}
      />
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
    <div className="fixed inset-0 z-20 bg-ink/40" role="presentation" onClick={onClose}>
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col overflow-hidden bg-surface shadow-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-prep-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="border-b border-border px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate">{SESSION_TYPES[session.type].label}</p>
              <h2 id="session-prep-title" className="mt-1 font-display text-xl text-ink">
                Session preparation
              </h2>
              <p className="mt-1 text-sm text-slate">Generated from this client&apos;s current context and prior sessions.</p>
            </div>
            <button type="button" className="text-slate transition-colors hover:text-ink" aria-label="Close" onClick={onClose}>
              <XIcon className="h-5 w-5" />
            </button>
          </div>
          <div className="mt-4 flex gap-0 border-b border-border">
            {(["prep", "review", "history"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                className={`border-b-2 px-4 pb-3 text-sm transition-colors ${
                  activeTab === tab ? "border-teal font-medium text-teal" : "border-transparent text-slate hover:text-ink"
                }`}
                onClick={() => onTabChange(tab)}
              >
                {tab === "prep" ? "Session prep" : tab === "review" ? "Last review" : "History"}
              </button>
            ))}
          </div>
        </header>
        <div className="flex-1 overflow-y-auto bg-surface px-6 py-6">
          {isLoading && <p className="text-sm text-slate">Building prep from the Context Library and prior sessions...</p>}
          {error && <p className="text-sm text-amber">Unable to load this session&apos;s preparation.</p>}
          {!isLoading && !error && data && activeTab === "prep" && (
            data.keypoints.length > 0 ? (
              <ul className="space-y-3">
                {data.keypoints.map((point, i) => (
                  <li
                    key={i}
                    className="flex gap-3 rounded-lg border border-border bg-surface-2 px-4 py-3 text-sm leading-6 text-ink"
                  >
                    <span className="text-teal">•</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate">No prep keypoints are available for this session yet.</p>
            )
          )}
          {!isLoading && !error && data && activeTab === "review" && (
            data.scorecard ? (
              <pre className="whitespace-pre-wrap font-body text-sm leading-6 text-ink">{JSON.stringify(data.scorecard, null, 2)}</pre>
            ) : (
              <p className="text-sm text-slate">No completed review is available for this session yet.</p>
            )
          )}
          {!isLoading && !error && data && activeTab === "history" && (
            data.history.length > 0 ? (
              <ul className="space-y-4">
                {data.history.map((item) => (
                  <li key={item.id} className="border-b border-border pb-4">
                    <p className="text-xs tabular-nums text-slate">{new Date(item.eventDate).toLocaleDateString()}</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{item.summary ?? "No sent summary is available."}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate">No prior sessions of this type are on file.</p>
            )
          )}
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
              <li key={rowIndex} className="flex items-center justify-between rounded-xl border border-border px-4 py-3">
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
  for (const session of sessions) grouped.set(session.clientId, [...(grouped.get(session.clientId) ?? []), session]);
  return grouped;
}
