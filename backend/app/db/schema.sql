-- CoachFlow schema — source of truth DDL (backend/CLAUDE.md).
-- Apply via Supabase migrations, or directly against local Postgres:
--   psql "$DATABASE_URL" -f app/db/schema.sql
--
-- Already provisioned a DB before the users.status column existed? Run by hand:
--   create type user_status as enum ('active', 'suspended', 'deleted');
--   alter table users add column status user_status not null default 'active';
--
-- Already provisioned a DB before users.must_reset_password existed? Run by hand:
--   alter table users add column if not exists must_reset_password boolean not null default false;
--
-- Already provisioned a DB before context_library.embedding existed? Run by hand:
--   create extension if not exists "vector";
--   alter table context_library add column if not exists embedding vector(768);
--   create index if not exists context_library_embedding_hnsw_idx
--       on context_library using hnsw (embedding vector_cosine_ops);
--   -- then paste the match_context_library function body from below (create or replace is safe to re-run)
--
-- Already provisioned a DB before per-user reminder rules/RLS existed? Run:
--   alter table reminder_rules add column if not exists user_id uuid references users(id) on delete cascade;
--   -- migrate any legacy rows to the intended coach user before making user_id not null;
--   alter table reminder_rules drop constraint if exists reminder_rules_pkey;
--   alter table reminder_rules add primary key (user_id, session_type);
--   alter table reminder_rules alter column user_id set not null;
--
-- Already provisioned a DB before import_jobs/import_items (the Drive
-- backfill) existed? Run by hand — safe to re-run even if a prior attempt
-- got partway through, e.g. failed on "relation already exists":
--   do $$ begin
--     create type import_source as enum ('calendar', 'context_library', 'client_notes', 'transcripts');
--   exception when duplicate_object then null; end $$;
--   do $$ begin
--     create type import_job_status as enum ('running', 'completed', 'failed');
--   exception when duplicate_object then null; end $$;
--   do $$ begin
--     create type import_item_status as enum ('imported', 'failed', 'unmatched_client');
--   exception when duplicate_object then null; end $$;
--   create table if not exists import_jobs (
--       id uuid primary key default gen_random_uuid(),
--       tenant_id text not null references tenants(id),
--       source import_source not null,
--       status import_job_status not null default 'running',
--       items_total int not null default 0,
--       items_succeeded int not null default 0,
--       items_failed int not null default 0,
--       error_message text,
--       started_at timestamptz not null default now(),
--       completed_at timestamptz
--   );
--   create table if not exists import_items (
--       id uuid primary key default gen_random_uuid(),
--       job_id uuid not null references import_jobs(id) on delete cascade,
--       tenant_id text not null references tenants(id),
--       source import_source not null,
--       drive_file_id text not null,
--       file_name text not null,
--       mime_type text not null,
--       status import_item_status not null,
--       client_id uuid references clients(id),
--       error_message text,
--       created_at timestamptz not null default now(),
--       unique (tenant_id, source, drive_file_id)
--   );
--   create index if not exists import_jobs_tenant_id_idx on import_jobs(tenant_id);
--   create index if not exists import_items_job_id_idx on import_items(job_id);
--   create index if not exists import_items_status_idx on import_items(status);
--
-- Already provisioned a DB before the privacy lockdown (RLS on every table,
-- no anon/authenticated grants, sessions.external_event_id,
-- transcripts.session_id, coach_briefings)? Run the idempotent script:
--   psql "$DATABASE_URL" -f app/db/patches/2026-09-18_privacy_lockdown.sql
--
-- Already provisioned before prompt_templates.description and the ICF
-- post-session templates existed? Run (idempotent, after the lockdown patch):
--   psql "$DATABASE_URL" -f app/db/patches/2026-09-19_icf_critique_and_prompt_descriptions.sql

create extension if not exists "pgcrypto";
create extension if not exists "vector";

create type user_role as enum ('admin', 'general');
create type user_status as enum ('active', 'suspended', 'deleted');
create type session_type as enum ('one_on_one', 'quarterly_review', 'annual_review', 'monthly_council');
create type session_status as enum ('upcoming', 'prep_generating', 'ready_for_review', 'sent');
create type transcript_source as enum ('plaud', 'gemini_meet');
create type parse_status as enum ('ok', 'partial', 'failed');
create type draft_type as enum ('reminder', 'summary', 'questionnaire', 'prep_email');
create type draft_status as enum ('pending', 'sent', 'rejected');
create type import_source as enum ('calendar', 'context_library', 'client_notes', 'transcripts');
create type import_job_status as enum ('running', 'completed', 'failed');
create type import_item_status as enum ('imported', 'failed', 'unmatched_client');

create table tenants (
    id text primary key,                       -- 'tenant_a' / 'tenant_b'
    workspace_domain text not null unique,
    encrypted_refresh_token text,               -- Fernet-encrypted; null until OAuth completed
    client_id text not null,
    client_secret_ref text not null,            -- secrets-manager reference, never the raw secret
    connected boolean not null default false,
    created_at timestamptz not null default now()
);

-- Mirrors Supabase Auth users; id must equal the auth.users id. status is a
-- single enum covering both suspend and soft-delete: 'suspended' and
-- 'deleted' both block authentication (enforced in core/security.py's
-- get_current_user), the only difference is 'deleted' users are also
-- excluded from the admin users list.
create table users (
    id uuid primary key,
    email text not null unique,
    role user_role not null default 'general',
    status user_status not null default 'active',
    -- true for every admin-provisioned account until the coach sets their own
    -- password (POST /api/auth/complete-password-reset clears it); the admin
    -- Create User flow always creates accounts with this set.
    must_reset_password boolean not null default false,
    assigned_client_ids uuid[] not null default '{}',
    created_at timestamptz not null default now()
);

create table clients (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null,                        -- send-to address for approved drafts
    coach_user_id uuid not null references users(id),
    tenant_id text not null references tenants(id),
    drive_folder_id text,
    session_types session_type[] not null default '{}',
    created_at timestamptz not null default now()
);

create table sessions (
    id uuid primary key default gen_random_uuid(),
    client_id uuid not null references clients(id) on delete cascade,
    type session_type not null,
    tenant_id text not null references tenants(id),
    event_date timestamptz not null,
    trigger_date timestamptz not null,          -- event_date minus the type's working-day lead time
    transcript_id uuid,                          -- fk added below after transcripts exists
    status session_status not null default 'upcoming',
    external_event_id text unique,               -- calendar event id; the scanner upserts on it so a
                                                 -- reschedule updates its own session and two clients'
                                                 -- sessions at the same time never merge
    created_at timestamptz not null default now()
);

create table unmatched_events (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id),
    raw_event_summary text not null,
    event_date timestamptz not null,
    resolved_session_type session_type,          -- set once the coach assigns a type in the Calendar view
    created_at timestamptz not null default now(),
    unique (tenant_id, raw_event_summary, event_date)
);

create table transcripts (
    id uuid primary key default gen_random_uuid(),
    file_ref text not null,                       -- Google Drive file id
    source transcript_source not null,
    normalized_text jsonb,                        -- list of {speaker, timestamp, text}
    parse_status parse_status not null default 'ok',
    session_id uuid references sessions(id) on delete set null, -- owner; null until linked to a session
    created_at timestamptz not null default now()
);

alter table sessions
    add constraint sessions_transcript_id_fkey
    foreign key (transcript_id) references transcripts(id);

-- Append-only: an edit never overwrites a row, it inserts the next version
-- under the same entry_group_id. context_library_current (below) exposes
-- just the latest version per group — context_builder.py reads that view,
-- never this table directly, so historical versions never reach the AI.
create table context_library (
    id uuid primary key default gen_random_uuid(),
    entry_group_id uuid not null default gen_random_uuid(),
    client_id uuid references clients(id) on delete cascade, -- null = org-wide (ICF/GROW docs)
    title text not null,                        -- required heading describing what this entry covers,
                                                 -- shown above the body in every assembled prompt so the
                                                 -- model can judge relevance among the entries it's given
    body text not null,
    embedding vector(768),                      -- computed at write time via models/gemini-embedding-2,
                                                 -- RETRIEVAL_DOCUMENT task_type; null for rows written
                                                 -- before this column existed until the backfill script runs
    version int not null default 1,
    created_at timestamptz not null default now()
);

create table scorecards (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions(id) on delete cascade,
    structured_critique jsonb not null,
    citations jsonb not null default '[]',
    created_at timestamptz not null default now()
);

create table ai_drafts (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions(id) on delete cascade,
    draft_type draft_type not null,
    tenant_id text not null references tenants(id),
    body text not null,
    status draft_status not null default 'pending',
    rejection_reason text,
    created_at timestamptz not null default now(),
    sent_at timestamptz
);

create table reminder_rules (
    user_id uuid not null references users(id) on delete cascade,
    session_type session_type not null,
    lead_time_working_days int not null,
    naming_pattern text not null,
    primary key (user_id, session_type)
);

-- Append-only, same shape as context_library: an edit posts a new version
-- under the same entry_group_id rather than overwriting. draft_generator.py
-- and scorecard_generator.py read prompt_templates_current (below) at
-- generation time — this table is the live source the AI actually uses,
-- not just an editor's backing store.
create table prompt_templates (
    id uuid primary key default gen_random_uuid(),
    entry_group_id uuid not null default gen_random_uuid(),
    session_type session_type not null,
    phase text not null check (phase in ('pre', 'post')),
    title text not null,                        -- clear heading, e.g. "1-on-1 — Pre-Session Prep"
    description text,                            -- what the prompt does, when it runs, what it produces
    body text not null,
    version int not null default 1,
    created_at timestamptz not null default now()
);

-- The internal coach briefing for a session (D-07): shown in the dashboard,
-- never approval-gated, never emailed, never stored in ai_drafts. Also caches
-- the generated prep so viewing a session doesn't re-send its client's data
-- to Gemini on every page load.
create table coach_briefings (
    session_id uuid primary key references sessions(id) on delete cascade,
    keypoints jsonb not null,
    created_at timestamptz not null default now()
);

create table tasks_sync (
    scorecard_id uuid not null references scorecards(id) on delete cascade,
    google_task_id text not null,
    primary key (scorecard_id, google_task_id)
);

create table metrics_log (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete set null,
    gemini_tokens int,
    gemini_latency_ms int,
    gemini_cost_usd numeric(10, 4),
    created_at timestamptz not null default now()
);

-- Backs the one-time Drive backfill of pre-existing calendar/context-library/
-- client-notes/transcript material (services/drive_backfill.py, triggered
-- from Admin > Import). Ongoing ingestion keeps using the live Calendar API
-- poll and the single-file /webhooks/drive inbox — these tables only track
-- the historical import runs, they're not a new ongoing pipeline.
create table import_jobs (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id),
    source import_source not null,
    status import_job_status not null default 'running',
    items_total int not null default 0,
    items_succeeded int not null default 0,
    items_failed int not null default 0,
    error_message text,                          -- set on a job-level failure (e.g. folder not accessible)
    started_at timestamptz not null default now(),
    completed_at timestamptz
);

-- One row per Drive file the backfill looked at. unique(tenant_id, source,
-- drive_file_id) lets re-running a source skip files already imported
-- instead of duplicating context_library/transcripts rows.
create table import_items (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references import_jobs(id) on delete cascade,
    tenant_id text not null references tenants(id),
    source import_source not null,
    drive_file_id text not null,
    file_name text not null,
    mime_type text not null,
    status import_item_status not null,
    client_id uuid references clients(id),        -- set once imported or manually resolved
    error_message text,
    created_at timestamptz not null default now(),
    unique (tenant_id, source, drive_file_id)
);

create index sessions_client_id_idx on sessions(client_id);
create index sessions_trigger_date_idx on sessions(trigger_date);
create index ai_drafts_status_idx on ai_drafts(status);
create index ai_drafts_tenant_id_idx on ai_drafts(tenant_id);
create index context_library_client_id_idx on context_library(client_id);
create index context_library_entry_group_id_idx on context_library(entry_group_id);
create index context_library_embedding_hnsw_idx on context_library using hnsw (embedding vector_cosine_ops);
create index prompt_templates_entry_group_id_idx on prompt_templates(entry_group_id);
create index prompt_templates_session_phase_idx on prompt_templates(session_type, phase);
create index import_jobs_tenant_id_idx on import_jobs(tenant_id);
create index import_items_job_id_idx on import_items(job_id);
create index import_items_status_idx on import_items(status);
create index reminder_rules_user_id_idx on reminder_rules(user_id);

-- Privacy lockdown. The browser holds the public anon key (for Supabase Auth
-- only) and never queries tables directly; every data read goes through the
-- backend, which connects with the service-role key (bypasses RLS) and
-- enforces per-client access itself (core/security.py). So the database
-- denies anon/authenticated by default: RLS on every table with no policies
-- except reminder_rules' own-row one, table/function grants revoked, and the
-- `_current` views run as the caller (security_invoker) so they can't be
-- used to read around RLS. Keep patches/2026-09-18_privacy_lockdown.sql in
-- sync with this block.
alter table tenants enable row level security;
alter table users enable row level security;
alter table clients enable row level security;
alter table sessions enable row level security;
alter table unmatched_events enable row level security;
alter table transcripts enable row level security;
alter table context_library enable row level security;
alter table scorecards enable row level security;
alter table ai_drafts enable row level security;
alter table coach_briefings enable row level security;
alter table prompt_templates enable row level security;
alter table tasks_sync enable row level security;
alter table metrics_log enable row level security;
alter table import_jobs enable row level security;
alter table import_items enable row level security;

alter table reminder_rules enable row level security;
create policy reminder_rules_own_data on reminder_rules
    for all to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- Latest version per logical entry/prompt. Everything that *reads* Context
-- Library or prompt template content (context_builder.py, draft_generator.py,
-- scorecard_generator.py) queries these views, never the raw append-only
-- tables above, so historical versions never leak into an AI prompt.
create view context_library_current with (security_invoker = true) as
    select distinct on (entry_group_id) *
    from context_library
    order by entry_group_id, version desc;

-- Ranked Context Library retrieval for context_builder.py. Only ranks
-- client-specific entries (client_id = filter_client_id) — org-wide
-- ICF/GROW docs are always included unranked by the caller, never filtered
-- through this function, since they're foundational regardless of
-- similarity score. Rows with no embedding yet (pre-migration, before the
-- backfill script runs) are excluded. Note: querying context_library_current
-- (a distinct-on view) means Postgres materializes the distinct-on before it
-- can sort by vector distance, so the HNSW index on the base table isn't
-- actually hit through this view — irrelevant at today's per-client row
-- counts (an index-free scan over a handful of rows is instant), kept for a
-- future direct-table query path.
create or replace function match_context_library(
    query_embedding vector(768),
    filter_client_id uuid,
    match_count int default 6
)
returns setof context_library_current
language sql
stable
as $$
    select *
    from context_library_current
    where client_id = filter_client_id
      and embedding is not null
    order by embedding <=> query_embedding
    limit match_count;
$$;

create view prompt_templates_current with (security_invoker = true) as
    select distinct on (entry_group_id) *
    from prompt_templates
    order by entry_group_id, version desc;

-- Seed prompt_templates with the text that used to live in app/ai/prompts/*.py
-- (now deleted — this table is the sole source draft_generator.py and
-- scorecard_generator.py read from). Dollar-quoted so the apostrophe in
-- "coach's performance" and the {curly braces} below don't need escaping.
insert into prompt_templates (session_type, phase, title, description, body, version) values
('one_on_one', 'pre', '1-on-1 Executive Coaching — Pre-Session Prep', 'Runs 3 working days before each 1-on-1 session (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past 1-on-1 sessions with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.', $tpl$You are preparing a coach for an upcoming 1-on-1 executive coaching session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior 1-on-1 sessions with this client (most recent first)
{prior_sessions}

Produce a JSON object with these keys:
- "greeting": a one-line salutation to the coach.
- "intro": one short sentence introducing what this prep covers.
- "keypoints": an array of strings — open threads from the last session,
  suggested GROW-model focus areas, and 2-3 questions worth raising, each
  as its own point. Ground every claim in the Context Library or
  prior-session material above — do not invent history.
- "signoff": a one-line closing.

Respond with JSON only, matching this shape exactly.
$tpl$, 1),
('one_on_one', 'post', '1-on-1 Executive Coaching — Post-Session ICF Critique & Summary', 'Runs when a 1-on-1 session transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.', $tpl$You are an experienced ICF assessor (MCC level) reviewing a 1-on-1 session that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A 1-on-1 executive coaching session with an individual. Pay particular attention to: the session agreement at the start (3.1–3.4); the GROW flow (Goal, Reality, Options, Way forward); presence and the quality of questions (competencies 5 and 7); and a close that turns insight into action with accountability the client designs (8.5–8.9).

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$, 1),
('quarterly_review', 'pre', 'Quarterly Strategic Review — Pre-Session Prep', 'Runs 5 working days before each Quarterly Strategic Review (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Quarterly Strategic Reviews with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.', $tpl$You are preparing a coach for an upcoming Quarterly Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Quarterly Strategic Reviews with this client (most recent first)
{prior_sessions}

Produce a JSON object with these keys:
- "greeting": a one-line salutation to the coach.
- "intro": one short sentence introducing what this prep covers.
- "keypoints": an array of strings — quarter-over-quarter progress against
  prior strategic goals and 2-3 focus areas for this review, each as its
  own point. Ground every claim in the material above.
- "signoff": a one-line closing.

Respond with JSON only, matching this shape exactly.
$tpl$, 1),
('quarterly_review', 'post', 'Quarterly Strategic Review — Post-Session ICF Critique & Summary', 'Runs when a Quarterly Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.', $tpl$You are an experienced ICF assessor (MCC level) reviewing a Quarterly Strategic Review that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A Quarterly Strategic Review, with an individual or a company team. Pay particular attention to: agreeing the quarter's strategic goals and how success is measured (3.1–3.4); evoking awareness of patterns across the quarter (6.5, 7.3, 7.4); and turning the review into next-quarter commitments (8.4–8.7). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$, 1),
('annual_review', 'pre', 'Annual Strategic Review — Pre-Session Prep', 'Runs 10 working days before each Annual Strategic Review (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Annual Strategic Reviews with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.', $tpl$You are preparing a coach for an upcoming Annual Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Annual Strategic Reviews with this client (most recent first)
{prior_sessions}

Produce a JSON object with these keys:
- "greeting": a one-line salutation to the coach.
- "intro": one short sentence introducing what this prep covers.
- "keypoints": an array of strings — year-over-year progress and 2-3 focus
  areas for this review, each as its own point. Ground every claim in the
  material above.
- "signoff": a one-line closing.

Respond with JSON only, matching this shape exactly.
$tpl$, 1),
('annual_review', 'post', 'Annual Strategic Review — Post-Session ICF Critique & Summary', 'Runs when a Annual Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.', $tpl$You are an experienced ICF assessor (MCC level) reviewing a Annual Strategic Review that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
An Annual Strategic Review, with an individual or a company team. Pay particular attention to: exploring the year's growth and who the client is becoming (5.1, 7.2, 8.2); acknowledging progress (8.8); and clear agreements for the year ahead (3.1–3.4). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$, 1),
('monthly_council', 'pre', 'Monthly Strategic Council — Pre-Session Prep', 'Runs 5 working days before each Monthly Strategic Council (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Monthly Strategic Councils with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.', $tpl$You are preparing a coach for an upcoming Monthly Strategic Council session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Monthly Strategic Council sessions with this client (most recent first)
{prior_sessions}

Produce a JSON object with these keys:
- "greeting": a one-line salutation to the coach.
- "intro": one short sentence introducing what this prep covers.
- "keypoints": an array of strings — open action items and 2-3 focus areas
  for this council session, each as its own point. Ground every claim in
  the material above.
- "signoff": a one-line closing.

Respond with JSON only, matching this shape exactly.
$tpl$, 1),
('monthly_council', 'post', 'Monthly Strategic Council — Post-Session ICF Critique & Summary', 'Runs when a Monthly Strategic Council transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.', $tpl$You are an experienced ICF assessor (MCC level) reviewing a Monthly Strategic Council that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A Monthly Strategic Council, with an individual or a company team. Pay particular attention to: holding focus and time (3.1, 5.3); challenging without attachment (7.5); and clear actions with accountability (8.6, 8.7). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$, 1);

-- Nothing in the public schema is reachable with the anon or authenticated
-- roles; see the privacy lockdown note above.
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on function match_context_library(vector, uuid, int) from public, anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from anon, authenticated;
