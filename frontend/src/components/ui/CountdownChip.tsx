/** Working-days-to-trigger indicator that sits next to a session's status
 * pill. Colour alone never carries the meaning — the aria-label always
 * states it in words (docs/ui-design-spec.md §6.1, §12). */
export function CountdownChip({ workingDaysLeft }: { workingDaysLeft: number }) {
  const tone =
    workingDaysLeft <= 0
      ? "bg-red-600 text-white"
      : workingDaysLeft < 2
        ? "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400"
        : workingDaysLeft <= 5
          ? "bg-amber/15 text-amber"
          : "bg-teal-soft text-teal";

  const label =
    workingDaysLeft <= 0
      ? "Overdue for trigger"
      : `${workingDaysLeft} working day${workingDaysLeft === 1 ? "" : "s"} to trigger`;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium tabular-nums ${tone}`}
      aria-label={label}
    >
      {label}
    </span>
  );
}
