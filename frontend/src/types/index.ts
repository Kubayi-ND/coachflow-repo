// Re-exports from shared/types, per frontend/CLAUDE.md. Once the backend's
// OpenAPI schema exists, wire an `openapi-typescript` generation step here
// too (pre-dev script, matching gen:session-types) so response shapes come
// from the backend instead of being hand-duplicated.
export * from "./sessionTypes.generated";

export type TenantId = "tenant_a" | "tenant_b";
export type UserRole = "admin" | "general";
export type UserStatus = "active" | "suspended" | "deleted";

export interface AppUser {
  id: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  assignedClientIds: string[];
}

export interface Client {
  id: string;
  name: string;
  email: string;
  coachUserId: string;
  tenantId: TenantId;
  driveFolderId: string | null;
  sessionTypes: import("./sessionTypes.generated").SessionTypeId[];
}

export type SessionStatus = "upcoming" | "prep_generating" | "ready_for_review" | "sent";

export interface Session {
  id: string;
  clientId: string;
  type: import("./sessionTypes.generated").SessionTypeId;
  tenantId: TenantId;
  eventDate: string;
  triggerDate: string;
  transcriptId: string | null;
  status: SessionStatus;
}

export interface UnmatchedEvent {
  id: string;
  tenantId: TenantId;
  rawEventSummary: string;
  eventDate: string;
  resolvedSessionType: import("./sessionTypes.generated").SessionTypeId | null;
}

export type DraftType = "reminder" | "summary" | "questionnaire" | "prep_email";
export type DraftStatus = "pending" | "sent" | "rejected";

export interface AiDraft {
  id: string;
  sessionId: string;
  draftType: DraftType;
  tenantId: TenantId;
  body: string;
  status: DraftStatus;
  rejectionReason: string | null;
}

export interface Scorecard {
  id: string;
  sessionId: string;
  structuredCritique: Record<string, unknown>;
  citations: Record<string, unknown>[];
}

export interface ContextLibraryEntry {
  id: string;
  entryGroupId: string;
  clientId: string | null; // null = org-wide (ICF/GROW docs)
  title: string; // required heading describing what this entry covers
  body: string;
  version: number;
  createdAt: string;
}

export interface PromptTemplate {
  id: string;
  entryGroupId: string;
  sessionType: import("./sessionTypes.generated").SessionTypeId;
  phase: "pre" | "post";
  title: string;
  body: string;
  version: number;
  createdAt: string;
}

export interface MetricsSummary {
  hoursSaved: number;
  avgSessionEndToDraftReadyMinutes: number;
  geminiTokenCostUsd: number;
  billableHourValueProtectedUsd: number;
  transcriptParseSuccessRateBySource: Record<string, number>;
  draftApprovalRateWithoutEdits: number;
  unmatchedEventsCount: number;
}
