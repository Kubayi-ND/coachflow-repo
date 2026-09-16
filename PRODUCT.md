# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are internal staff at a single executive-coaching practice: the coach (`general` role) and the practice admin (`admin` role). Both are daily operators of the tool, not the coachees — coachees never interact with CoachFlow directly; the system drafts communications on their behalf for the coach to review and send.

## Product Purpose

CoachFlow replaces a manual, multi-tool coaching workflow (Plaud recorder → Google Drive → Gemini Notebook → Obsidian prompts → manual email) with one system. It watches Google Calendar for four recurring session types (driving five workflow phases, A–E), ingests meeting transcripts (Plaud exports, Gemini Meet transcripts, and Teams captions), builds AI-assembled prep and post-session evaluations grounded in a coaching Context Library (ICF competencies + GROW model), and drafts every client-facing communication — but never sends anything without the coach approving it first.

## Positioning

The mechanism a competitor could not casually copy: AI drafts are grounded in a versioned, ranked Context Library (embedding-based retrieval over ICF/GROW material, not free-floating LLM output) with citations back to source entries, and nothing reaches a client without a human-in-the-loop approval gate enforced as a single, architectural Gmail-send code path — not a UI convention that could be bypassed elsewhere in the codebase.

## Operating Context

Two Google Workspace tenants are built (multi-tenant within Google, not single-tenant); the spec's third tenant, Microsoft 365, is designed but its build is deferred pending client confirmation (`docs/decisions.md` D-05). Every client/session/draft carries a `tenant_id`, and the send step always reads that tenant back rather than re-deriving it, so a Tenant B client can never be emailed from Tenant A's identity.

Four recurring session types across five workflow phases (A–E), each type with its own calendar-naming convention and working-day lead time: 1-on-1 Executive Coaching, Quarterly Strategic Review, Annual Strategic Review, Monthly Strategic Council. Quarterly, annual and monthly sessions can be held with an individual or with a company team (D-02); engagements are kept separate — nothing from an individual reaches a team unless the coach deliberately shares it after an explicit warning, and individuals never see each other's information (D-03).

Five-view daily coach workflow, in the order a coach actually uses them:
1. **Calendar** — upcoming sessions across both tenants, countdown per session type's lead time, status chips, and an "unmatched events" exception queue for calendar events the naming-convention scanner couldn't classify.
2. **Approvals inbox** — the core loop. Every pending AI draft (reminder / summary / questionnaire / prep email), always showing which tenant/mailbox a send will come from. Actions: approve & send, edit then approve, reject with a reason.
3. **Clients** — directory across both tenants; detail page links to Drive folder structure and shows Context Library entries + session-type configuration.
4. **Scorecards** — read-only, internal-only ICF/GROW critique per session, with citations back to the Context Library section it was grounded in.
5. **Metrics** — ops dashboard (admin + coach): hours saved, draft-ready latency, token cost vs. billable-hour value, transcript parse success rate by source, draft approval-without-edits rate, unmatched-events count.

A separate Admin/Context Library area exists alongside the five main views: tenant credential status, reminder-rule editor, prompt template editor, Context Library editor (org-wide or client-specific ICF/GROW entries), and user management. As of the current codebase, the reminder-rule editor, prompt template editor, and Context Library editor are accessible to both `admin` and `general` roles (`require_coach_or_admin`) — coaches can now use this shared tooling, not just admins. Tenant connection status and user management remain admin-only (`require_admin`).

## Capabilities and Constraints

- Auth: Supabase Auth issues a JWT on login; the backend verifies it against Supabase's JWKS and enforces role/tenant/client authorization server-side (in the repository/service layer, not just hidden UI) — the frontend never relies on hiding elements as the only gate.
- Frontend stack: React 18 + TypeScript + Vite, React Router 6, TanStack Query for all server state (no hand-rolled `useEffect` fetching), TanStack Table for the client list/session history/metrics tables, Recharts for the Metrics view's charts, react-hook-form + zod for forms, date-fns for working-day lead-time math.
- Design tokens already defined and in active use (not to be invented fresh): `paper`/`ink`/`teal`/`teal-soft`/`amber`/`slate`, each with a light and dark value; `amber` is semantically reserved for pending/attention states (reminders, unmatched events). Fraunces for display/headings only, Public Sans for body/UI, `font-variant-numeric: tabular-nums` on every numeric column.
- The frontend never calls Google APIs or the Gemini API directly, and never queries Supabase tables directly for app data (auth session only) — all data reads/writes go through the backend API.
- Constraint for this pass specifically: preserve every existing route, interaction, and data flow. This is a visual/UX refinement, not a rebuild or feature change.

## Brand Commitments

Name: CoachFlow. No logo or broader visual identity exists beyond the token palette and font pairing already defined in `frontend/CLAUDE.md` — those are binding starting material for any redesign work, not optional input to be replaced.

## Evidence on Hand

No user research, screenshots, or reference sites were provided for this pass. The existing implementation (current React components, Tailwind usage, and token application) is the primary evidence of incumbent visual truth and should be treated as such before proposing changes.

## Product Principles

1. Human-in-the-loop must never read as ambiguous — no UI state should make an unapproved draft feel sent, or make "pending" and "sent" hard to tell apart at a glance.
2. Tenant/mailbox identity must always be visible where a send decision is being made, especially the Approvals inbox.
3. This is an operational daily-use tool, not a marketing surface — scanability and consistent interaction patterns outrank expressive visual flourish.
4. AI output should read as grounded, not black-box — scorecards and drafts should let the coach trace claims back to their Context Library source via citations.
5. Private coaching conversations stay private — any moment where individual content could reach a team (sharing it, or approving a team draft that uses it) must be visibly flagged and require a deliberate, acknowledged action.

## Accessibility & Inclusion

No explicit standard has been confirmed for this project. Given the small, internal user base, no specific regulatory requirement is known, but WCAG AA is the reasonable baseline for an interactive daily-use dashboard.
