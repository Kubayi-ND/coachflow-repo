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

create table context_library (
    id uuid primary key default gen_random_uuid(),
    client_id uuid references clients(id) on delete cascade, -- null = org-wide (ICF/GROW docs)
    title text not null,
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

create table prompt_templates (
    session_type session_type not null,
    phase text not null check (phase in ('pre', 'post')),
    body text not null,
    version int not null default 1,
    primary key (session_type, phase)
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

-- Seed the four session types' default lead times/naming (root CLAUDE.md table).
-- The Admin > reminder-rule editor lets a coach tune these later.
insert into reminder_rules (session_type, lead_time_working_days, naming_pattern) values
    ('one_on_one', 3, 'Grow Executive Coaching [Coachee Name]'),
    ('quarterly_review', 5, 'Grow Quarterly Strategic Review'),
    ('annual_review', 10, 'Grow Annual Strategic Review'),
    ('monthly_council', 5, 'Grow Monthly Strategic Council');
