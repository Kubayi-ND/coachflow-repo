import { differenceInCalendarDays, format, isToday, isTomorrow, isYesterday } from "date-fns";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { CopyButton } from "@/components/ui/CopyButton";
import { CountdownChip } from "@/components/ui/CountdownChip";
import { Pill } from "@/components/ui/Pill";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatTile } from "@/components/ui/StatTile";
import { AlertTriangleIcon, CalendarIcon, ChevronRightIcon, CheckCircleIcon, UsersIcon, XIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { IcfCritique } from "@/features/scorecards/IcfCritique";
import { useClients } from "@/hooks/useClients";
import { analysisErrorMessage, useRunAnalysis, useScorecard } from "@/hooks/useScorecard";
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

type PrepTab = "prep" | "critique" | "review" | "history";

export function CalendarView() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [activeTab, setActiveTab] = useState<PrepTab>("prep");
  const { data: clients } = useClients();
  const { data: sessions, isLoading } = useSessions();
  const { data: unmatchedEvents } = useUnmatchedEvents();
  const resolveEvent = useResolveUnmatchedEvent();
  const prepQuery = useSessionPrep(selectedSession?.id ?? null);
  const clientsById = new Map((clients ?? []).map((client) => [client.id, client]));
  const sessionsByDay = groupByDay(sessions ?? []);

  return (
    <div className="space-y-8">
      <section>
        <QuickStats clients={clients ?? []} sessions={sessions ?? []} unmatchedCount={unmatchedEvents?.length ?? 0} />

        {isLoading && <CalendarSkeleton />}

        {!isLoading && sessionsByDay.length === 0 && (
          <p className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-slate">
            No sessions on the calendar yet. Sessions appear here once the calendar scan matches an event.
          </p>
        )}

        <div className="space-y-6">
          {sessionsByDay.map(([day, daySessions]) => (
            <div key={day}>
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="text-sm font-semibold text-ink">{dayLabel(day)}</h2>
                <span className="text-xs text-slate">{relativeDays(day)}</span>
              </div>
              <ul className="space-y-2">
                {daySessions.map((session) => {
                  const client = clientsById.get(session.clientId);
                  return (
                    <li key={session.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4 text-left shadow-card transition-all duration-150 hover:border-teal/30 hover:shadow-cardmd"
                        onClick={() => {
                          setSelectedSession(session);
                          setActiveTab("prep");
                        }}
                      >
                        <div className="flex min-w-0 items-center gap-4">
                          <span className="flex-shrink-0 rounded-md bg-surface-2 px-2 py-1 font-mono text-xs tabular-nums text-ink">
                            {format(new Date(session.eventDate), "HH:mm")}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-ink">{client?.name ?? "Unknown client"}</p>
                            <p className="mt-0.5 text-xs text-slate">{SESSION_TYPES[session.type].label}</p>
                          </div>
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
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {unmatchedEvents && unmatchedEvents.length > 0 && (
        <section id="unmatched-events" className="scroll-mt-6">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangleIcon className="h-4 w-4 text-amber" />
            <h2 className="text-sm font-semibold text-amber">Unmatched events</h2>
            <span className="tabular-nums text-xs text-amber/80">({unmatchedEvents.length})</span>
          </div>
          <p className="mb-3 text-sm text-slate">
            Calendar events that weren&apos;t matched to one client automatically: unknown titles, sessions that may
            be with a team, or invites with more than one client on them. Assign a type so nothing is missed.
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
          clientName={clientsById.get(selectedSession.clientId)?.name}
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
      {unmatchedCount > 0 ? (
        <a
          href="#unmatched-events"
          className="rounded-xl transition-shadow hover:shadow-cardmd focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
          aria-label={`${attentionCount} need attention, jump to unmatched events`}
        >
          <StatTile label="Need attention" value={attentionCount} icon={<AlertTriangleIcon className="h-5 w-5" />} tone="amber" />
        </a>
      ) : (
        <StatTile
          label="Need attention"
          value={attentionCount}
          icon={<AlertTriangleIcon className="h-5 w-5" />}
          tone={attentionCount > 0 ? "amber" : "neutral"}
        />
      )}
    </div>
  );
}

function SessionPrepDrawer({ session, clientName, data, isLoading, error, activeTab, onTabChange, onClose }: {
  session: Session;
  clientName: string | undefined;
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
              <p className="mt-2 text-xs text-slate">
                Confidential · uses {clientName ?? "this client"}&apos;s records only
              </p>
            </div>
            <button type="button" className="text-slate transition-colors hover:text-ink" aria-label="Close" onClick={onClose}>
              <XIcon className="h-5 w-5" />
            </button>
          </div>
          <div className="mt-4 flex gap-0 border-b border-border">
            {(["prep", "critique", "review", "history"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                className={`border-b-2 px-4 pb-3 text-sm transition-colors ${
                  activeTab === tab ? "border-teal font-medium text-teal" : "border-transparent text-slate hover:text-ink"
                }`}
                onClick={() => onTabChange(tab)}
              >
                {TAB_LABEL[tab]}
                {tab === "history" && data ? ` (${data.history.length})` : ""}
              </button>
            ))}
          </div>
        </header>
        <div className="flex-1 overflow-y-auto bg-surface px-6 py-6">
          {activeTab === "critique" && <SessionCritique session={session} />}
          {activeTab !== "critique" && isLoading && (
            <p className="text-sm text-slate">Building prep from the Context Library and prior sessions...</p>
          )}
          {activeTab !== "critique" && error && (
            <p className="text-sm text-amber">Unable to load this session&apos;s preparation.</p>
          )}
          {!isLoading && !error && data && activeTab === "prep" && (
            data.keypoints.length > 0 ? (
              <div className="space-y-3">
                <div className="flex justify-end">
                  <CopyButton text={data.keypoints.map((point) => `- ${point}`).join("\n")} label="Copy all" />
                </div>
                <ul className="space-y-3">
                  {data.keypoints.map((point, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 rounded-lg border border-border bg-surface-2 px-4 py-3 text-sm leading-6 text-ink"
                    >
                      <span className="text-teal">•</span>
                      <span className="flex-1">{point}</span>
                      <CopyButton text={point} ariaLabel="Copy this point" />
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-slate">No prep keypoints are available for this session yet.</p>
            )
          )}
          {!isLoading && !error && data && activeTab === "review" && (
            data.scorecard ? (
              <IcfCritique critique={data.scorecard} citations={data.citations} />
            ) : (
              <p className="text-sm leading-6 text-slate">
                No critique from the previous {SESSION_TYPES[session.type].label} yet. Critiques appear once a
                session&apos;s transcript has been analysed.
              </p>
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

const TAB_LABEL: Record<PrepTab, string> = {
  prep: "Session prep",
  critique: "ICF critique",
  review: "Last review",
  history: "History",
};

/** This session's own post-session ICF critique: shown once generated,
 * otherwise an Analyse button (when a transcript is linked) or an
 * explanation of when it becomes available. */
function SessionCritique({ session }: { session: Session }) {
  const { data: scorecard, isLoading } = useScorecard(session.id);
  const runAnalysis = useRunAnalysis();
  const toast = useToast();

  function analyse(refresh: boolean) {
    runAnalysis.mutate(
      { sessionId: session.id, refresh },
      {
        onSuccess: () => toast.show(refresh ? "Critique regenerated." : "Critique ready."),
        onError: (error) => toast.show(analysisErrorMessage(error), "error"),
      }
    );
  }

  if (isLoading) return <p className="text-sm text-slate">Loading critique...</p>;
  if (scorecard) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-end gap-3">
          <Link to={`/sessions/${session.id}/scorecard`} className="text-xs font-medium text-teal hover:underline">
            Open full page
          </Link>
          <Button variant="secondary" size="sm" onClick={() => analyse(true)} isLoading={runAnalysis.isPending}>
            Analyse again
          </Button>
        </div>
        <IcfCritique critique={scorecard.structuredCritique} citations={scorecard.citations} />
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-dashed border-border px-5 py-6">
      <p className="text-sm font-medium text-ink">No ICF critique for this session yet</p>
      <p className="mt-2 text-sm leading-6 text-slate">
        {session.transcriptId
          ? "The transcript is linked. Run the analysis to rate this session against the ICF core competencies and PCC markers, with quotes as evidence. It also drafts a client summary for your approval."
          : "It runs automatically once this session's transcript arrives, and rates your coaching against the ICF core competencies and PCC markers."}
      </p>
      {session.transcriptId && (
        <Button className="mt-4" size="sm" onClick={() => analyse(false)} isLoading={runAnalysis.isPending}>
          Analyse session
        </Button>
      )}
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

/** Sessions grouped by calendar day (yyyy-MM-dd, local time), days and
 * sessions in time order — how a coach plans the week. */
function groupByDay(sessions: Session[]): [string, Session[]][] {
  const sorted = [...sessions].sort((a, b) => new Date(a.eventDate).getTime() - new Date(b.eventDate).getTime());
  const grouped = new Map<string, Session[]>();
  for (const session of sorted) {
    const day = format(new Date(session.eventDate), "yyyy-MM-dd");
    grouped.set(day, [...(grouped.get(day) ?? []), session]);
  }
  return [...grouped.entries()];
}

function dayLabel(day: string): string {
  const date = new Date(`${day}T00:00:00`);
  if (isToday(date)) return "Today";
  if (isTomorrow(date)) return "Tomorrow";
  if (isYesterday(date)) return "Yesterday";
  return format(date, "EEEE d MMMM");
}

function relativeDays(day: string): string {
  const days = differenceInCalendarDays(new Date(`${day}T00:00:00`), new Date());
  if (days === 0) return "today";
  if (days > 0) return `in ${days} day${days === 1 ? "" : "s"}`;
  return `${-days} day${days === -1 ? "" : "s"} ago`;
}
