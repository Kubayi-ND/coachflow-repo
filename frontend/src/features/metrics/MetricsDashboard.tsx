import { useQuery } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetch } from "@/lib/apiClient";
import type { MetricsSummary } from "@/types";

/** Operations dashboard, not a report — summary tiles first, detail tables
 * below, and falling approval-without-edits rate is a visual flag
 * (frontend/CLAUDE.md). */
export function MetricsDashboard() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => apiFetch<MetricsSummary>("/api/metrics"),
  });

  if (isLoading || !metrics) return <MetricsDashboardSkeleton />;

  const approvalRatePercent = Math.round(metrics.draftApprovalRateWithoutEdits * 100);
  const approvalRateFalling = approvalRatePercent < 70;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl">Metrics</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Tile label="Hours saved" value={metrics.hoursSaved.toFixed(1)} />
        <Tile label="Gemini token cost" value={`$${metrics.geminiTokenCostUsd.toFixed(2)}`} />
        <Tile
          label="Draft approval rate"
          value={`${approvalRatePercent}%`}
          flagged={approvalRateFalling}
        />
        <Tile label="Unmatched events" value={String(metrics.unmatchedEventsCount)} />
        <Tile
          label="Avg. draft-ready time"
          value={`${Math.round(metrics.avgSessionEndToDraftReadyMinutes)} min`}
        />
        <Tile label="Billable value protected" value={`$${metrics.billableHourValueProtectedUsd.toFixed(0)}`} />
      </div>

      <section>
        <h2 className="text-lg mb-2">Transcript parse success rate by source</h2>
        <table className="text-sm">
          <tbody>
            {Object.entries(metrics.transcriptParseSuccessRateBySource).map(([source, rate]) => (
              <tr key={source}>
                <td className="pr-4 py-1 capitalize">{source.replace("_", " ")}</td>
                <td className="tabular-nums py-1">{Math.round(rate * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Tile({ label, value, flagged }: { label: string; value: string; flagged?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${flagged ? "border-amber bg-amber/5" : "border-slate/20"}`}>
      <p className="text-xs text-slate">{label}</p>
      <p className="text-2xl tabular-nums mt-1">{value}</p>
    </div>
  );
}

function MetricsDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl">Metrics</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-slate/20 p-4">
            <Skeleton className="h-3 w-24 mb-3" />
            <Skeleton className="h-7 w-16" />
          </div>
        ))}
      </div>

      <section>
        <h2 className="text-lg mb-2">Transcript parse success rate by source</h2>
        <table className="text-sm">
          <tbody>
            {Array.from({ length: 3 }).map((_, i) => (
              <tr key={i}>
                <td className="pr-4 py-1">
                  <Skeleton className="h-4 w-28" />
                </td>
                <td className="py-1">
                  <Skeleton className="h-4 w-10" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
