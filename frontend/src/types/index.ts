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
  mustResetPassword: boolean;
  assignedClientIds: string[];
}

/** POST /api/admin/users response — the temporary password is returned once
 * and never stored, so the admin must copy it to hand to the coach directly. */
export interface CreateUserResult {
  user: AppUser;
  temporaryPassword: string;
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

/** POST /api/clients body. coachUserId is never sent — a client is always
 * self-assigned to the authenticated coach creating it, server-side. */
export interface ClientCreateInput {
  name: string;
  email: string;
  tenantId: TenantId;
  driveFolderId?: string | null;
  sessionTypes?: import("./sessionTypes.generated").SessionTypeId[];
  /** Optional freeform coaching context — seeded server-side as a
   * client-scoped Context Library entry, not stored on the client itself. */
  context?: string;
}

export type ClientUpdateInput = Partial<Omit<ClientCreateInput, "context">>;

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

export interface SessionPrep {
  session: Session;
  keypoints: string[];
  scorecard: Record<string, unknown> | null;
  citations: Record<string, unknown>[];
  history: { id: string; eventDate: string; summary: string | null }[];
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

export type ImportSource = "calendar" | "context_library" | "client_notes" | "transcripts";
export type ImportJobStatus = "running" | "completed" | "failed";
export type ImportItemStatus = "imported" | "failed" | "unmatched_client";

/** Backs the Admin > Import page's one-time Drive backfill of pre-existing
 * calendar/context-library/client-notes/transcript folders. Not part of the
 * ongoing ingestion pipeline (live Calendar poll, transcript inbox webhook),
 * which keeps running unchanged after a backfill completes. */
export interface ImportJob {
  id: string;
  tenantId: TenantId;
  source: ImportSource;
  status: ImportJobStatus;
  itemsTotal: number;
  itemsSucceeded: number;
  itemsFailed: number;
  errorMessage: string | null;
  startedAt: string;
  completedAt: string | null;
}

export interface ImportItem {
  id: string;
  jobId: string;
  tenantId: TenantId;
  source: ImportSource;
  driveFileId: string;
  fileName: string;
  mimeType: string;
  status: ImportItemStatus;
  clientId: string | null;
  errorMessage: string | null;
  createdAt: string;
}

