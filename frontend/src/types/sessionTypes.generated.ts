// AUTO-GENERATED from shared/types/session-types.json. Do not edit by hand.
// Regenerate: node shared/types/scripts/generate-session-types.ts

export type SessionTypeId = "one_on_one" | "quarterly_review" | "annual_review" | "monthly_council";

export interface SessionTypeDefinition {
  id: SessionTypeId;
  label: string;
  namingPattern: string;
  leadTimeWorkingDays: number;
}

export const SESSION_TYPES: Record<SessionTypeId, SessionTypeDefinition> = {
  one_on_one: {
    id: "one_on_one",
    label: "1-on-1 Executive Coaching",
    namingPattern: "Grow Executive Coaching [Coachee Name]",
    leadTimeWorkingDays: 3,
  },
  quarterly_review: {
    id: "quarterly_review",
    label: "Quarterly Strategic Review",
    namingPattern: "Grow Quarterly Strategic Review",
    leadTimeWorkingDays: 5,
  },
  annual_review: {
    id: "annual_review",
    label: "Annual Strategic Review",
    namingPattern: "Grow Annual Strategic Review",
    leadTimeWorkingDays: 10,
  },
  monthly_council: {
    id: "monthly_council",
    label: "Monthly Strategic Council",
    namingPattern: "Grow Monthly Strategic Council",
    leadTimeWorkingDays: 5,
  },
};

export const SESSION_TYPE_IDS: SessionTypeId[] = [
  "one_on_one",
  "quarterly_review",
  "annual_review",
  "monthly_council",
];
