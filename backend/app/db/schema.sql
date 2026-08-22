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
    created_at timestamptz not null default now()
);

create table unmatched_events (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id),
    raw_event_summary text not null,
    event_date timestamptz not null,
    resolved_session_type session_type,          -- set once the coach assigns a type in the Calendar view
    created_at timestamptz not null default now()
);

create table transcripts (
    id uuid primary key default gen_random_uuid(),
    file_ref text not null,                       -- Google Drive file id
    source transcript_source not null,
    normalized_text jsonb,                        -- list of {speaker, timestamp, text}
    parse_status parse_status not null default 'ok',
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
    body text not null,
    version int not null default 1,
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

-- RLS is enabled even though the API uses a service-role connection. These
-- policies protect direct Supabase access and document the data boundary;
-- API routes still enforce the same authenticated-user checks explicitly.
alter table context_library enable row level security;
create policy context_library_authenticated_access on context_library
    for all to authenticated using (true) with check (true);

alter table reminder_rules enable row level security;
create policy reminder_rules_own_data on reminder_rules
    for all to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- Latest version per logical entry/prompt. Everything that *reads* Context
-- Library or prompt template content (context_builder.py, draft_generator.py,
-- scorecard_generator.py) queries these views, never the raw append-only
-- tables above, so historical versions never leak into an AI prompt.
create view context_library_current as
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

create view prompt_templates_current as
    select distinct on (entry_group_id) *
    from prompt_templates
    order by entry_group_id, version desc;

-- Seed prompt_templates with the text that used to live in app/ai/prompts/*.py
-- (now deleted — this table is the sole source draft_generator.py and
-- scorecard_generator.py read from). Dollar-quoted so the apostrophe in
-- "coach's performance" and the {curly braces} below don't need escaping.
insert into prompt_templates (session_type, phase, title, body, version) values
('one_on_one', 'pre', '1-on-1 Executive Coaching — Pre-Session Prep', $tpl$You are preparing a coach for an upcoming 1-on-1 executive coaching session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior 1-on-1 sessions with this client (most recent first)
{prior_sessions}

Draft a prep email to the coach summarizing: open threads from the last
session, suggested GROW-model focus areas for this session, and 2-3 questions
worth raising. Ground every claim in the Context Library or prior-session
material above — do not invent history. Write in plain prose, ready to send
after coach review.
$tpl$, 1),
('one_on_one', 'post', '1-on-1 Executive Coaching — Post-Session Scorecard & Summary', $tpl$You are producing the post-session artifacts for a 1-on-1 executive coaching
session that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Produce a JSON object with two top-level keys:
- "scorecard": a structured ICF/GROW critique of the coach's performance in
  this session, with a "citations" array linking each claim back to the
  specific Context Library section id it was grounded in. This is internal
  only — do not soften findings for a client audience.
- "client_summary": a plain-prose session summary suitable for the
  client-facing draft, focused on their stated goals and next steps only —
  no internal critique content.

Respond with JSON only, matching this shape exactly.
$tpl$, 1),
('quarterly_review', 'pre', 'Quarterly Strategic Review — Pre-Session Prep', $tpl$You are preparing a coach for an upcoming Quarterly Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Quarterly Strategic Reviews with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing quarter-over-quarter progress against prior
strategic goals and 2-3 focus areas for this review. Ground every claim in
the material above.
$tpl$, 1),
('quarterly_review', 'post', 'Quarterly Strategic Review — Post-Session Scorecard & Summary', $tpl$You are producing the post-session artifacts for a Quarterly Strategic Review
that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
$tpl$, 1),
('annual_review', 'pre', 'Annual Strategic Review — Pre-Session Prep', $tpl$You are preparing a coach for an upcoming Annual Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Annual Strategic Reviews with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing year-over-year progress and 2-3 focus areas
for this review. Ground every claim in the material above.
$tpl$, 1),
('annual_review', 'post', 'Annual Strategic Review — Post-Session Scorecard & Summary', $tpl$You are producing the post-session artifacts for an Annual Strategic Review
that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
$tpl$, 1),
('monthly_council', 'pre', 'Monthly Strategic Council — Pre-Session Prep', $tpl$You are preparing a coach for an upcoming Monthly Strategic Council session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Monthly Strategic Council sessions with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing open action items and 2-3 focus areas for this
council session. Ground every claim in the material above.
$tpl$, 1),
('monthly_council', 'post', 'Monthly Strategic Council — Post-Session Scorecard & Summary', $tpl$You are producing the post-session artifacts for a Monthly Strategic Council
session that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
$tpl$, 1);
