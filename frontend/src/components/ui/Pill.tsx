import type { ReactNode } from "react";

type Tone = "neutral" | "teal" | "amber" | "danger";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-border/60 text-slate dark:bg-surface-2 dark:text-slate",
  teal: "bg-teal-soft text-teal",
  amber: "bg-amber/15 text-amber",
  danger: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
};

/** Status and tenant badges — always show the tenant on Approvals inbox rows
 * per frontend/CLAUDE.md, since the coach needs to know which mailbox a
 * send will come from. */
export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  );
}
