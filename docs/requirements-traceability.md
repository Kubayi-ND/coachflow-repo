# CoachFlow — Requirements Traceability

Maps every requirement in the official spec
([`grow-hackathon-case-study.md`](grow-hackathon-case-study.md)) and every agreed
clarification ([`decisions.md`](decisions.md)) to its implementation status and
the milestone that closes it. **Update this file in every PR that changes one of
these rows.**

Status: **Done** · **Partial** · **Missing** · **Conflict** (code contradicts the spec) · **Deferred** (agreed deviation, see decisions)

Milestones: M0 docs alignment · M1 migrations + security lockdown · M2 blockers + session lifecycle · M3 engagements + separation · M4 calendar ingestion + tenant connection · M5 RAG · M6 pre-session phases A/C/D/E · M7 post-session phase B · M8 observability + metrics · M9 provider-neutral tenants · M10 deliverable docs

_Last reviewed: 2026-09-18 (privacy lockdown — see [`handoffs/2026-09-18-privacy-lockdown-and-rag-audit.md`](handoffs/2026-09-18-privacy-lockdown-and-rag-audit.md))._

## §3 A — Pre-session preparation (1-on-1)

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Scan the primary calendar for `Grow Executive Coaching [Coachee Name]` | Partial | Title matching works; the live scanner writes sessions without a client, which the schema rejects | M4 |
| Run exactly 3 working days before | Partial | Working-day calculation exists; no SA public holidays (D-04) | M4 |
| Internal coach briefing with notes and action items from the immediately prior session | Conflict | History never reaches prompts (sessions are never marked `sent`), there's no action item data, and the briefing is saved as a client-facing draft (D-07) | M2, M6 |
| Client email: session date/time | Missing | — | M6 |
| Client email: unresolved action items from the last session | Missing | Action items aren't captured | M6, M7 |
| Client email: request agenda items | Missing | — | M6 |
| Sent from the correct originating tenant | Done | Approve re-reads the draft's `tenant_id` | — |

## §3 B — Post-session analysis & quality critique

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Triggered by session end + transcript availability | Partial | Runs when a transcript is linked (Drive webhook links only an unambiguous recent session; backfills link by nearest session) and on demand from the dashboard. No session-end trigger yet | M7 |
| Ingest Plaud transcripts | Done | Header skipped, `[hh:mm:ss]` timestamps kept, damaged lines mark the parse `partial`; speakers still mapped by order | — |
| Ingest Gemini transcripts | Partial | JSON and "Meeting Notes" Markdown exports parse; Gemini notes as Google Docs aren't handled | M7 |
| Ingest MS Teams transcripts | Missing | No `.vtt`/`.srt` parser; Graph deferred (D-05) | M7, M9 |
| Critique against the Context Library (ICF + GROW) | Done | ICF rubric (8 competencies, 37 PCC markers) with transcript evidence; citations validated against the retrieved rows. Retrieval is still whole-document (M5) | — |
| Internal scorecard saved to the coach's files | Missing | Stored in the database only, not Drive | M7 |
| Client summary email with takeaways + action items | Done | Created as a pending Approvals draft by the post-session analysis | — |
| Coach action items posted to Google Tasks | Missing | `create_task` exists, never called | M7 |

## §3 C — Quarterly Strategic Review

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Identify QSR on the calendar | Partial | Title match only; individual vs team unresolved (D-02, D-08) | M4 |
| 5 working days before | Partial | See D-04 | M4 |
| Aggregate the past 3 months of Monthly Strategic Council sessions | Conflict | Code only pulls past sessions of the same type (D-06) | M6 |
| Coach notification: last quarter's outcomes + pending strategic actions | Partial | Single prep output, no action items | M2, M6 |
| AI identifies recurring themes across the client's history | Missing | — | M6 |
| Client email with a pre-filled strategic questionnaire | Missing | — | M6 |

## §3 D — Annual Strategic Review

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Identify ASR; 10 working days before | Partial | See D-04, D-08 | M4 |
| Coach notification covering the year | Conflict | Pulls past annual reviews only, not the year's sessions (D-06) | M6 |
| Client prep email setting deep-dive expectations | Partial | Single mixed output (D-07) | M2, M6 |

## §3 E — Monthly Strategic Council

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Identify council; 5 working days before | Partial | See D-04, D-08 | M4 |
| Coach notification covering the month | Conflict | Pulls past councils only (D-06) | M6 |
| Client prep email setting council expectations | Partial | Single mixed output (D-07) | M2, M6 |

## §3 Data & technology footprint

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| 2× Google Workspace tenants | Partial | No OAuth connect flow; tokens must be inserted by hand | M4 |
| 1× Microsoft 365 / Exchange tenant | Deferred | D-05 | M9 (design) |
| Calendar API v3 JSON payloads | Done | — | — |
| Transcripts: text, vtt/srt, markdown | Partial | Text only | M7 |
| Context Library: Markdown, PDF, Google Docs from Drive | Done | One-time Drive/local backfill with PDF/DOCX/Docs extraction | — |

## §4 Constraints, risks & assumptions

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| OAuth tokens handled securely, no cross-tenant leakage | Partial | Encrypted per-tenant vault and single send path exist; no connect flow. CORS now limited to `CORS_ALLOWED_ORIGINS` | M4, M9 |
| Ambiguous QSR/ASR naming handled | Partial | Unmatched queue exists, but assigning a type doesn't create a session | M4 |
| Transcript variability & speaker labels | Partial | See §3 B rows | M7 |
| Objective, structured, grounded AI critique | Done | Fixed ICF rubric, validated output, citation and quote checks, readable critique view | — |
| Confidential recordings & transcripts stay inside Grow's environment | Partial | Done in code: RLS on every table with anon/authenticated grants revoked, and every route that exposes client data scoped to assigned clients. Pending: the lockdown patch isn't applied to the live project yet; unmatched calendar events are visible to every coach; prompts go to Gemini unredacted (paid-tier key required) | M1, M3 |
| ASM-001 standard titles | Partial | 1-on-1 only; see D-08 | M4 |
| ASM-002 transcripts machine-readable via API/webhook/drop | Partial | Drive Inbox webhook only | M7 |
| ASM-003 central Context Library folder | Done | Backfill importer | — |
| CON-001 three email identities without cross-contamination | Partial | Two Google tenants; Microsoft deferred | M4, M9 |
| CON-002 3/5/10 working-day lead times from calendar parsing | Done | SA holidays added in M4 (D-04) | M4 |

## §5 Role deliverables & scoring criteria

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| BA: As-Is vs To-Be process map with human approval | Missing | — | M10 |
| BA: exception handling (reschedule inside the window, failed transcript upload) | Missing | Reschedules create duplicate sessions; no missing-transcript detection; failed generation leaves sessions stuck | M4, M7, M10 |
| Data: KPIs & ROI (hours saved, pipeline speed, token cost vs billable time) | Missing | Metrics endpoint returns placeholders; cost never calculated; no page | M8 |
| Data: transcript standardization mapping design | Missing | — | M7, M10 |
| Dev: integration pipeline proof of concept (calendar trigger → historical data) | Partial | Chain exists but is broken at client linking and history | M2–M6 |
| Dev: multi-tenant auth architecture incl. Microsoft Graph | Missing | — | M9 |
| Human-in-the-loop review & edit of drafts | Partial | Approve / edit / reject works; briefing wrongly treated as a client draft | M2 |
| Scannable, actionable output | Partial | ICF critique rendered as cards with strengths, growth areas and action items; prep is still flat bullets | M6 |
| Observability: performance, token cost, processing errors | Missing | Errors only in logs; tokens logged only by the unused scorecard step | M8 |

## Agreed after the spec

| Requirement | Status | Notes | Milestone |
|---|---|---|---|
| Individual vs team engagements, any session type for either (D-02) | Missing | No company or team concept | M3 |
| Nothing from an individual reaches a team by default; individuals never see each other (D-03) | Partial | Done: one retrieval-scope function (`context_builder.resolve_retrieval_scope`) re-checks every row; only 1-on-1s with exactly one known attendee auto-match. Pending: there's no company/team model yet, and client notes still flow into every session type for that client | M3, M4 |
| Coach can share individual → team with a required warning; shares are logged and revocable (D-03) | Missing | — | M3 |
| Internal briefing separate from client draft (D-07) | Partial | `coach_briefings` stores the dashboard prep; the reminder job still writes its prep as an `ai_drafts` row | M2 |
| Supabase CLI migrations (D-09) | Missing | — | M1 |
