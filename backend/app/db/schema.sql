-- CoachFlow schema — source of truth DDL (backend/CLAUDE.md).
-- Apply via Supabase migrations, or directly against local Postgres:
--   psql "$DATABASE_URL" -f app/db/schema.sql

create extension if not exists "pgcrypto";

create type user_role as enum ('admin', 'general');
create type session_type as enum ('one_on_one', 'quarterly_review', 'annual_review', 'monthly_council');
create type session_status as enum ('upcoming', 'prep_generating', 'ready_for_review', 'sent');
create type transcript_source as enum ('plaud', 'gemini_meet');
create type parse_status as enum ('ok', 'partial', 'failed');
create type draft_type as enum ('reminder', 'summary', 'questionnaire', 'prep_email');
create type draft_status as enum ('pending', 'sent', 'rejected');

create table tenants (
    id text primary key,                       -- 'tenant_a' / 'tenant_b'
    workspace_domain text not null unique,
    encrypted_refresh_token text,               -- Fernet-encrypted; null until OAuth completed
    client_id text not null,
    client_secret_ref text not null,            -- secrets-manager reference, never the raw secret
    connected boolean not null default false,
    created_at timestamptz not null default now()
);

-- Mirrors Supabase Auth users; id must equal the auth.users id.
create table users (
    id uuid primary key,
    email text not null unique,
    role user_role not null default 'general',
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
    session_type session_type primary key,
    lead_time_working_days int not null,
    naming_pattern text not null
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

create index sessions_client_id_idx on sessions(client_id);
create index sessions_trigger_date_idx on sessions(trigger_date);
create index ai_drafts_status_idx on ai_drafts(status);
create index ai_drafts_tenant_id_idx on ai_drafts(tenant_id);
create index context_library_client_id_idx on context_library(client_id);
create index context_library_entry_group_id_idx on context_library(entry_group_id);
create index prompt_templates_entry_group_id_idx on prompt_templates(entry_group_id);
create index prompt_templates_session_phase_idx on prompt_templates(session_type, phase);

-- Latest version per logical entry/prompt. Everything that *reads* Context
-- Library or prompt template content (context_builder.py, draft_generator.py,
-- scorecard_generator.py) queries these views, never the raw append-only
-- tables above, so historical versions never leak into an AI prompt.
create view context_library_current as
    select distinct on (entry_group_id) *
    from context_library
    order by entry_group_id, version desc;

create view prompt_templates_current as
    select distinct on (entry_group_id) *
    from prompt_templates
    order by entry_group_id, version desc;

-- Seed the four session types' default lead times/naming (root CLAUDE.md table).
-- The Admin > reminder-rule editor lets a coach tune these later.
insert into reminder_rules (session_type, lead_time_working_days, naming_pattern) values
    ('one_on_one', 3, 'Grow Executive Coaching [Coachee Name]'),
    ('quarterly_review', 5, 'Grow Quarterly Strategic Review'),
    ('annual_review', 10, 'Grow Annual Strategic Review'),
    ('monthly_council', 5, 'Grow Monthly Strategic Council');

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
