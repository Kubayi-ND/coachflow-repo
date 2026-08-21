import { describe, expect, it } from "vitest";

import { subtractWorkingDays } from "@/lib/workingDays";

describe("subtractWorkingDays", () => {
  it("skips a weekend when subtracting 3 working days from a Friday", () => {
    // Friday 2026-08-21 minus 3 working days -> Tuesday 2026-08-18
    const result = subtractWorkingDays(new Date(2026, 7, 21), 3);
    expect(result.toDateString()).toBe(new Date(2026, 7, 18).toDateString());
  });

  it("spans two weekends when subtracting 10 working days", () => {
    // Monday 2026-08-24 minus 10 working days -> Monday 2026-08-10
    const result = subtractWorkingDays(new Date(2026, 7, 24), 10);
    expect(result.toDateString()).toBe(new Date(2026, 7, 10).toDateString());
  });
});
