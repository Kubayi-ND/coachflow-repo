import { isWeekend, subDays } from "date-fns";

/**
 * Subtracts N *working* days (Mon-Fri) from a date, skipping weekends.
 * Must match backend/app/services/calendar_scanner.py's add_working_days
 * exactly — both compute the same trigger/countdown dates from the same
 * inputs (frontend/CLAUDE.md: "lead-time countdowns must count working days,
 * not calendar days").
 */
export function subtractWorkingDays(start: Date, workingDays: number): Date {
  let current = start;
  let remaining = workingDays;
  while (remaining > 0) {
    current = subDays(current, 1);
    if (!isWeekend(current)) {
      remaining -= 1;
    }
  }
  return current;
}

/** Working days remaining between now and a trigger date, for the Calendar
 * view's countdown chip. Negative once the trigger date has passed. */
export function workingDaysUntil(target: Date, from: Date = new Date()): number {
  let count = 0;
  let current = from;
  const direction = target >= from ? 1 : -1;

  while (current.toDateString() !== target.toDateString()) {
    current = subDays(current, -direction);
    if (!isWeekend(current)) {
      count += direction;
    }
  }
  return count;
}
