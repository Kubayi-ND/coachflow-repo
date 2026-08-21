import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

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
  if (!scorecard) return <p className="text-slate">No scorecard found for this session.</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl">Scorecard</h1>
      <pre className="rounded-md border border-slate/20 p-4 text-xs overflow-auto">
        {JSON.stringify(scorecard.structuredCritique, null, 2)}
      </pre>
      <section>
        <h2 className="text-lg mb-2">Citations</h2>
        <ul className="space-y-1 text-sm text-slate">
          {scorecard.citations.map((citation, i) => (
            <li key={i}>{JSON.stringify(citation)}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ScorecardSkeleton() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl">Scorecard</h1>
      <div className="rounded-md border border-slate/20 p-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-full" />
        ))}
      </div>
      <section>
        <h2 className="text-lg mb-2">Citations</h2>
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
