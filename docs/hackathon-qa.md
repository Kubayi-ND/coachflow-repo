# CoachFlow — Hackathon Q&A Prep

A rehearsal doc for likely judge/audience questions, organized by the four roles on
the team. Each answer is grounded in what's actually built today, not the aspirational
pitch — where something is incomplete, seeded-but-untested, or a deliberate MVP
shortcut, that's called out explicitly so nobody gets caught flat-footed live.

Quick orientation if you only read one paragraph: **CoachFlow replaces a manual
five-tool workflow** (Plaud recorder → Google Drive → Gemini Notebook → Obsidian
prompts → manual email) **with one system**, for a single executive-coaching practice
running across **two Google Workspace tenants**. It watches Calendar for recurring
session types, ingests transcripts, drafts AI prep/summary/follow-up content grounded
in a versioned Context Library, and **never sends anything to a client without the
coach approving it first**.

---

## Cheat sheet (fast recall)

| Fact | Answer |
|---|---|
| Frontend | React 18 + TypeScript + Vite, TanStack Query/Table, Tailwind, react-hook-form + zod |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | Supabase (Postgres), `pgvector` for embeddings |
| Auth | Supabase Auth → JWT → backend verifies against Supabase's JWKS (no shared secret) |
| AI | Gemini API (`google-generativeai`), plus a self-hosted Ollama (`llama3.1:8b` on Railway) added alongside it for confidentiality-sensitive paths |
| Tenants | 2 (`tenant_a`, `tenant_b`) — every client/session/draft row carries `tenant_id` |
| Session types implemented | 4: `one_on_one`, `quarterly_review`, `annual_review`, `monthly_council` (docs describe "five" — see Known Gaps) |
| Human-in-the-loop gate | `ai_drafts.status = pending` → coach approves/rejects in the Approvals inbox → **only** `POST /api/drafts/{id}/approve` may call Gmail |
| Roles | `admin` (tenants, Context Library, prompt templates, reminder rules, user management) and `general`/coach (assigned clients, Approvals inbox, scorecards) |
| Retrieval | Ranked Context Library RAG: org-wide ICF/GROW docs always included unranked; client-specific entries ranked by `pgvector` cosine similarity via a `match_context_library` RPC |

---

## Business Analyst

**Q: What problem does this actually solve, in one sentence?**
A coach was manually stitching together a recorder, Drive, an AI notebook, a prompt
library, and email to prep for and follow up on every session. CoachFlow collapses
that into one system that watches the calendar, files transcripts, drafts everything
AI-assisted, and requires one click to send — replacing a five-tool, mostly-manual
workflow with a single reviewed inbox.

**Q: Who are the users, and what do they each get?**
Two roles: the **coach** (`general`) works within their assigned clients, lives in the
Approvals inbox, and reviews scorecards. The **admin** additionally manages tenants,
the Context Library, prompt templates, reminder rules, and user accounts. As of the
current build, the reminder-rule/prompt-template/Context-Library editors are shared by
both roles — coaches aren't locked out of that tooling anymore, only tenant connection
status and user management stay admin-only.

**Q: Why "human-in-the-loop" as a hard requirement rather than full automation?**
Because the product is client-facing correspondence written by an LLM on a coach's
behalf. Nothing generated is trustworthy enough to send unreviewed, and the risk of a
wrong or tone-deaf email reaching a paying client is high. So every draft — reminder,
summary, questionnaire, prep email — lands in `ai_drafts` with `status = pending` and
sits there until a human acts. This isn't a UI convention; it's enforced as a single
code path (see the Developer section).

**Q: Why two tenants instead of one?**
The coaching practice actually operates two separate Google Workspace domains. A
client's calendar, Drive folder, and outbound email must all come from the correct
domain's identity — sending from the wrong tenant would be a real trust breach, not a
cosmetic bug. The system is explicitly "multi-tenant within Google," scoped down from
a broader identity-provider-agnostic design to keep the hackathon build achievable.

**Q: What happens when a calendar event doesn't match one of the known session types?**
It's not silently dropped. `calendar_scanner.py` writes it to an `unmatched_events`
table, and the Calendar view surfaces an "Unmatched events" section where the coach
assigns a type with one click. This was explicitly designed as the answer to "what if
naming conventions drift" rather than leaving an unmatchable event as a silent gap.

**Q: What's out of scope for this build?**
Microsoft/Teams integration (the root spec explicitly scopes this iteration to
Google Workspace only, with Microsoft support designed to slot in later as a third
tenant row plus an `integrations/microsoft` package, not a rewrite), and — per the
current router — the Metrics dashboard view described in the product spec hasn't been
built as a page yet (see Known Gaps).

---

## Data Analyst

**Q: Walk me through the data model at a high level.**
Twelve core tables in Postgres (via Supabase): `tenants`, `users`, `clients`,
`sessions`, `unmatched_events`, `transcripts`, `context_library`, `scorecards`,
`ai_drafts`, `reminder_rules`, `prompt_templates`, plus `tasks_sync` and `metrics_log`
for observability, and `import_jobs`/`import_items` for one-time Drive backfills.
Every tenant-scoped table carries `tenant_id`; every session carries a `type` enum and
a computed `trigger_date` (event date minus that type's working-day lead time).

**Q: How does the AI grounding (RAG) actually work?**
`context_library` holds ICF-competency and GROW-model reference material, either
org-wide (`client_id = null`) or client-specific. Each row gets a 768-dimension
embedding from `models/gemini-embedding-2` at write time. At generation time,
`context_builder.py` always includes the org-wide entries unranked (they're
foundational regardless of similarity) and ranks client-specific entries by cosine
distance via a Postgres `pgvector` HNSW index, called through a `match_context_library`
RPC function (the standard pattern for vector search from `supabase-py`, which has no
raw SQL client). Every scorecard claim carries a citation back to the specific
Context Library entry it was grounded in.

**Q: Is the append-only versioning on Context Library and prompt templates actually
enforced, or just a convention?**
Enforced structurally: `context_library` and `prompt_templates` are insert-only,
keyed by an `entry_group_id` that stays stable across versions while `version`
increments. Nothing ever updates a row in place. Two SQL views —
`context_library_current` and `prompt_templates_current` — expose only the latest
version per group via `distinct on (entry_group_id) ... order by version desc`, and
every read path the AI actually uses (`context_builder.py`, `draft_generator.py`,
`scorecard_generator.py`) queries those views, never the raw tables. So a bad edit is
always recoverable by history, and a stale version can never accidentally leak into a
live prompt.

**Q: What can you actually measure/report on?**
`metrics_log` captures Gemini token count, latency, and cost per session. The product
spec's intended Metrics view would report: hours saved, time from session-end to
draft-ready, token cost vs. billable-hour value protected, transcript parse success
rate by source (`plaud` vs. `gemini_meet`), draft approval rate without edits, and
unmatched-events count. The logging exists; the dashboard aggregating it into that
view does not yet (see Known Gaps) — today those numbers would need a manual query.

**Q: Be honest — is there real data behind the RAG demo, or is it wired but empty?**
Wired but currently empty in the live database. `context_library` has no seed rows in
`schema.sql` (unlike `reminder_rules` and `prompt_templates`, which do ship seeded
data), and as of the last working session the table was confirmed empty live — nobody
has yet watched the ranking function return real, differentiated results against
populated data. The retrieval code itself is unit-tested (mocked embeddings/Supabase),
and the schema migration is live-confirmed, but a demo that needs to *show* ranked
retrieval working needs real Context Library entries added first.

**Q: How is tenant data isolation enforced at the data layer, not just the API?**
Row-level security is enabled on `context_library` and `reminder_rules` even though
the API connects with a service-role key — RLS here documents and protects the data
boundary for direct Supabase access, while the actual authorization for API traffic is
enforced explicitly in the backend's repository layer (see Developer section), not
left to RLS alone.

---

## Developer

**Q: How is "never send without approval" actually enforced in code, not just policy?**
By construction: `draft_generator.py` never imports or calls the Gmail integration —
it only ever writes to `ai_drafts` with `status = pending`. The **only** function in
the entire backend permitted to call `integrations/google/gmail.py` is the handler
behind `POST /api/drafts/{id}/approve`, which re-reads the draft's `tenant_id` off the
row (not re-derived from request context) before sending, so a Tenant B client can
never be emailed from Tenant A's identity even by a bug elsewhere. There's no second
code path to audit for a bypass — there's exactly one send call site in the codebase.

**Q: Why FastAPI + a separately deployed React SPA instead of a monolith?**
Clean separation of concerns for a system that holds real OAuth credentials and API
keys: the frontend never talks to Google APIs or holds the Supabase service-role
key directly — it only calls the backend's REST API and Supabase Auth for login. That
keeps every credential-holding surface in one process, independently deployable and
independently scalable (frontend → static host; backend → a container platform with a
scheduler for the polling jobs).

**Q: Why two AI backends (Gemini and a self-hosted Ollama model)?**
Confidentiality. Transcript content is sensitive, and routing it through a third-party
API by default raised concerns, so a second client (`ollama_client.py`, running
`llama3.1:8b` on Railway) was added alongside — not replacing — Gemini for the
confidentiality-sensitive generation paths. This is explicitly an MVP-stage decision:
CPU-only inference on Railway benchmarks at roughly 0.14 tokens/sec, which is
impractical for a live demo of that path. The team knowingly declined a bigger compute
tier or GPU (cost/scope reasons) and declined exposing the service on a public domain
(it has no built-in auth) — it's reachable only over Railway's private network. If
asked "why not make it faster," the honest answer is: two known options (bump compute,
or drop to a smaller model) were surfaced and deliberately deferred, not overlooked.

**Q: How do you handle schema migrations?**
Honestly, this is the roughest edge in the stack: there's no Alembic or formal
migration tool. `schema.sql` is the source-of-truth DDL, edited directly, with
"apply by hand" SQL blocks documented at the top of the file for each historical
change, run manually against the Supabase SQL Editor. In practice the live database
has drifted behind `schema.sql` more than once in the same build session — a column
or even a Postgres function (`match_context_library`) existing in the file but not
live yet, which look like code bugs but are actually just an unapplied change. The
practical mitigation the team adopted: verify against the live DB with a direct query
before debugging a "column/function does not exist" error, and always run a hand-applied
SQL block as one single submission (a split submission caused a partial-apply failure
once). This would be the first thing to fix — Alembic or Supabase's migration
CLI — past hackathon scope.

**Q: How is authorization enforced — frontend routing, or something deeper?**
Every backend route depends on a `get_current_user` dependency that verifies the
Supabase-issued JWT against Supabase's JWKS endpoint (no shared secret to manage,
no separate backend session — the JWT is the only credential). A second dependency
gates admin-only routes. Critically, for `general`-role users, every service function
touching a `client_id` checks it against that user's assigned clients **in the
repository layer**, not just the route handler — so a new route can't accidentally
skip the check by construction. The frontend also hides admin-only UI, but that's
treated as a UX nicety, never the actual security boundary.

**Q: What's the testing strategy?**
Backend: `pytest` + `httpx`, with every Google and Gemini call mocked (`unittest.mock`
/ `respx`) — CI never makes a live external call. At least one integration test per
core workflow phase (calendar-match → context-build → draft-generate) runs against
fixtures end to end, since a regression in that chain is one the coach would notice
immediately. Frontend: Vitest + React Testing Library for components, Playwright for
the two flows that matter most operationally — login and the Approvals inbox.

**Q: What would break first if you added a third tenant or a Microsoft integration?**
By design, not much at the data layer — `tenant_id` is already a first-class column
everywhere, and the credential vault pattern (`tenants` table holding one encrypted
token set per tenant, resolved per-request, never cached across requests) generalizes
directly. A Microsoft tenant was explicitly scoped as "a new tenant row and a new
`integrations/microsoft` package," not a rewrite. The naming-convention scanner and
session-type enum would need to become more flexible if a third org has different
calendar-naming habits, since those are currently a fixed enum matched against fixed
strings.

---

## Project Manager

**Q: What's actually done vs. still aspirational in the product spec?**
Done: the full session lifecycle (calendar scan → transcript ingest → context assembly
→ AI draft/scorecard generation → approval → send), the Approvals inbox, Clients
directory + detail, Scorecards view, Context Library + prompt-template editors (both
append-only with version history), Admin user management with forced password reset,
a one-time Drive backfill importer, and — most recently — a full visual redesign of
the dashboard into a modern sidebar/card layout. Not yet built: the Metrics
dashboard page (the backing `metrics_log` table and per-call logging exist; the
aggregating UI does not), and the Context Library has no real content loaded yet, so
the ranked-retrieval feature is implemented and tested but not yet demonstrably
"grounding" a real answer end to end.

**Q: What's the single biggest demo risk?**
An empty `context_library` table. The differentiator this whole system claims over "just
prompting an LLM" is that its output is grounded in a versioned, ranked knowledge base
with citations — but that table has no seed data live today, so a live demo of "look,
it cited its source" needs real ICF/GROW entries added first, or it needs to be
demoed against fixtures instead of the live system.

**Q: What deliberate scope cuts were made, and why?**
Three, all traceable decisions rather than gaps discovered late: (1) Microsoft/Teams
support was cut from this iteration and designed as a slot-in later addition, keeping
the Google-only build achievable. (2) The self-hosted Ollama path runs on
CPU-only Railway compute at a deliberately-accepted ~0.14 tokens/sec, because the team
chose MVP-scope cost over paying for GPU/bigger tier. (3) Formal database migrations
(Alembic) were skipped in favor of a hand-applied `schema.sql`, accepted knowingly as
technical debt to fix post-hackathon.

**Q: How is the team's decision-making evidenced, not just asserted?**
Every non-obvious architectural pivot lives in the codebase as an explanatory comment
tied to the decision, not just a commit message: the Ollama client's confidentiality
rationale, the reasoning for the RAG design (org-wide unranked + client-specific
ranked), and the schema-drift mitigation are all documented inline where a future
contributor — or a judge reading the code — would actually need them.

**Q: What would the next sprint prioritize?**
In order: (1) seed real Context Library content so the RAG differentiator is
demonstrable, not just implemented; (2) build the Metrics dashboard page against the
already-logging `metrics_log` data; (3) introduce a real migration tool to stop the
schema-drift class of bug; (4) revisit Ollama compute once real usage/cost data exists
from the Gemini path to justify the spend.

---

## Known Gaps (say this proactively if asked "what would you change")

- **Docs vs. implementation mismatch on session-type count.** The root spec's prose
  says "five recurring session types" in several places, but only four are actually
  defined — in the shared enum, the database's `session_type` type, and the seeded
  prompt templates: `one_on_one`, `quarterly_review`, `annual_review`,
  `monthly_council`. `docs/` is meant to be the reconciled source of truth per the
  project's own convention, but the original design write-up was never dropped into
  the repo to resolve the discrepancy — it's a documentation gap, not a missing
  feature, and worth naming plainly rather than guessing at a fifth type live.
- **Context Library has no seed data** — see Data Analyst / PM sections above.
- **Metrics dashboard view is not yet built** as a frontend page.
- **No formal DB migration tooling** — `schema.sql` + hand-applied SQL, with confirmed
  live drift incidents.
- **Ollama path is not demo-fast** — CPU-only, ~0.14 tokens/sec, by deliberate choice.
