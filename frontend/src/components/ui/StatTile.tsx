import type { ReactNode } from "react";

type Tone = "teal" | "amber" | "neutral";

const RING_CLASSES: Record<Tone, string> = {
  teal: "bg-teal-soft text-teal",
  amber: "bg-amber/15 text-amber",
  neutral: "bg-surface-2 text-slate",
};

const TREND_CLASSES: Record<"teal" | "amber", string> = {
  teal: "text-teal/80",
  amber: "text-amber",
};

interface StatTileProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  tone?: Tone;
  trend?: string;
  trendTone?: "teal" | "amber";
}

/** Top-of-view KPI block — every dashboard view leads with these so the
 * coach reads what needs attention before scrolling (docs/ui-design-spec.md
 * §7.5). Value + label form a dl/dt/dd pair so screen readers announce
 * "Active clients: 12" rather than "12 Active clients". */
export function StatTile({ label, value, icon, tone = "neutral", trend, trendTone = "teal" }: StatTileProps) {
  return (
    <dl className="rounded-xl border border-border bg-surface px-5 py-4 shadow-card">
      {icon && <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-full ${RING_CLASSES[tone]}`}>{icon}</div>}
      <dd className="font-display text-3xl tabular-nums text-ink">{value}</dd>
      <dt className="mt-1 text-xs text-slate">{label}</dt>
      {trend && <p className={`mt-2 text-[11px] ${TREND_CLASSES[trendTone]}`}>{trend}</p>}
    </dl>
  );
}
