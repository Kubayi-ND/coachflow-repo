import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { JsonTree } from "@/components/ui/JsonTree";
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
    <div className="space-y-6">
      <h1 className="text-2xl">Scorecard</h1>
      <div className="rounded-md border border-slate/20 p-4">
        <JsonTree value={scorecard.structuredCritique} />
      </div>
      {scorecard.citations.length > 0 && (
        <section>
          <h2 className="text-lg mb-2">Citations</h2>
          <p className="mb-2 text-xs text-slate">Every claim above should trace back to one of these Context Library sections.</p>
          <div className="rounded-md border border-slate/20 p-4">
            <JsonTree value={scorecard.citations} />
          </div>
        </section>
      )}
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
