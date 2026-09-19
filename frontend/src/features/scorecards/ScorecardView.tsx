import { useParams } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Skeleton } from "@/components/ui/Skeleton";
import { analysisErrorMessage, useRunAnalysis, useScorecard } from "@/hooks/useScorecard";
import { IcfCritique } from "./IcfCritique";

/** The coach-only post-session ICF critique, with citations back into the
 * Context Library entries it was grounded in so the coach can check the AI
 * isn't inventing a competency framework (frontend/CLAUDE.md). */
export function ScorecardView() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { data: scorecard, isLoading } = useScorecard(sessionId);
  const runAnalysis = useRunAnalysis();
  const toast = useToast();

  function analyse(refresh: boolean) {
    if (!sessionId) return;
    runAnalysis.mutate(
      { sessionId, refresh },
      {
        onSuccess: () => toast.show(refresh ? "Critique regenerated." : "Critique ready."),
        onError: (error) => toast.show(analysisErrorMessage(error), "error"),
      }
    );
  }

  if (isLoading) return <ScorecardSkeleton />;
  if (!scorecard) {
    return (
      <div className="mx-auto max-w-3xl rounded-xl border border-border bg-surface p-6 shadow-card">
        <h2 className="font-display text-lg text-ink">No ICF critique yet</h2>
        <p className="mt-2 text-sm leading-6 text-slate">
          Once this session&apos;s transcript is linked, CoachFlow rates your coaching against the ICF core
          competencies and PCC markers, with quotes from the session as evidence.
        </p>
        <Button className="mt-4" onClick={() => analyse(false)} isLoading={runAnalysis.isPending}>
          Analyse session
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={() => analyse(true)} isLoading={runAnalysis.isPending}>
          Analyse again
        </Button>
      </div>
      <IcfCritique critique={scorecard.structuredCritique} citations={scorecard.citations} />
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
