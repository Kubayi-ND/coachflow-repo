import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { JsonTree } from "@/components/ui/JsonTree";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetch } from "@/lib/apiClient";
import type { Scorecard } from "@/types";

/** Read-only ICF/GROW critique with citations back into the Context Library
 * section it was grounded in — exists so the coach can sanity-check the AI
 * isn't hallucinating a competency framework (frontend/CLAUDE.md): link
 * every claim to its source doc. */
export function ScorecardView() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const { data: scorecard, isLoading } = useQuery({
    queryKey: ["scorecard", sessionId],
    queryFn: () => apiFetch<Scorecard>(`/api/scorecards/${sessionId}`),
    enabled: !!sessionId,
  });

  if (isLoading) return <ScorecardSkeleton />;
  if (!scorecard) return <p className="text-sm text-slate">No scorecard found for this session.</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <Pill tone="teal">ICF / GROW</Pill>
        <div className="mt-3 rounded-lg bg-surface-2 p-4">
          <JsonTree value={scorecard.structuredCritique} />
        </div>
      </div>
      {scorecard.citations.length > 0 && (
        <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate">Citations</h2>
          <p className="mb-3 text-xs text-slate">Every claim above should trace back to one of these Context Library sections.</p>
          <div className="rounded-lg border border-border bg-surface-2 p-4">
            <JsonTree value={scorecard.citations} />
          </div>
        </section>
      )}
    </div>
  );
}

function ScorecardSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card space-y-3">
        <Skeleton className="h-5 w-20 rounded-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-full" />
        ))}
      </div>
      <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate">Citations</h2>
        <ul className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i}>
              <Skeleton className="h-3 w-3/4" />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
