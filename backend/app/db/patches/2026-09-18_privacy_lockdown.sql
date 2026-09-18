-- Privacy lockdown for a database provisioned from an older schema.sql.
-- Idempotent: safe to re-run. Brings an existing DB to the same state as the
-- current schema.sql (keep the two in sync).
--
--   psql "$DATABASE_URL" -f app/db/patches/2026-09-18_privacy_lockdown.sql
--
-- Before running against the live project, check what anon/authenticated
-- can currently reach (Supabase SQL editor):
--   select grantee, table_name, privilege_type
--   from information_schema.role_table_grants
--   where table_schema = 'public' and grantee in ('anon', 'authenticated');

begin;

-- 1. Ownership columns ------------------------------------------------------

alter table sessions add column if not exists external_event_id text;
create unique index if not exists sessions_external_event_id_key on sessions(external_event_id);

alter table transcripts add column if not exists session_id uuid references sessions(id) on delete set null;
-- Backfill the owner for transcripts already linked from a session.
update transcripts t
set session_id = s.id
from sessions s
where s.transcript_id = t.id and t.session_id is null;

-- calendar_scanner.py upserts unmatched events on this key; drop exact
-- duplicates (keeping the earliest) so the unique index can be created.
delete from unmatched_events a
using unmatched_events b
where a.tenant_id = b.tenant_id
  and a.raw_event_summary = b.raw_event_summary
  and a.event_date = b.event_date
  and a.created_at > b.created_at;
create unique index if not exists unmatched_events_tenant_summary_date_key
    on unmatched_events(tenant_id, raw_event_summary, event_date);

create table if not exists coach_briefings (
    session_id uuid primary key references sessions(id) on delete cascade,
    keypoints jsonb not null,
    created_at timestamptz not null default now()
);

-- 2. Row-level security on every table, no anon/authenticated policies ----

drop policy if exists context_library_authenticated_access on context_library;

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

-- 3. Views run as the caller, so they can't be used to read around RLS ----

alter view context_library_current set (security_invoker = true);
alter view prompt_templates_current set (security_invoker = true);

-- 4. Revoke direct access ----------------------------------------------------

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on function match_context_library(vector, uuid, int) from public, anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from anon, authenticated;

commit;
