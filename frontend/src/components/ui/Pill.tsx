import type { ReactNode } from "react";

type Tone = "neutral" | "teal" | "amber";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-slate/10 text-slate",
  teal: "bg-teal-soft text-teal",
  amber: "bg-amber/10 text-amber",
};

/** Status and tenant badges — always show the tenant on Approvals inbox rows
 * per frontend/CLAUDE.md, since the coach needs to know which mailbox a
 * send will come from. */
export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  );
}
