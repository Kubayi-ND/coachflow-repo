# CoachFlow — Backend

The orchestrator. This is the only component that ever holds Google OAuth credentials or calls the Gemini API — every automated action in the system (matching a calendar trigger, filing a transcript, building AI context, drafting an email, sending it, pushing a task) happens here, so tenant isolation and human-in-the-loop gating only need to be enforced in one place.

## Stack

- **Python 3.11+**, **FastAPI** for the HTTP API, **Pydantic v2** for schemas
- **google-api-python-client** + **google-auth** — Calendar, Drive, Gmail, Tasks, per tenant
- **google-generativeai** (Gemini SDK) — all AI calls
- **supabase-py** or direct **SQLAlchemy (async) + asyncpg** against the Supabase Postgres connection string — pick one and be consistent; `supabase-py` is simpler for a hackathon-scale build, SQLAlchemy is better if the team wants migrations via Alembic
- **APScheduler** (in-process, simplest) or **Celery + Redis** (if the team wants a real job queue) for the two recurring jobs: calendar polling and the reminder/lead-time check
- **python-jose** — verifies Supabase-issued JWTs against Supabase's JWKS endpoint
- **cryptography (Fernet)** — encrypts OAuth refresh tokens at rest in the tenant vault
- **pytest + httpx** — testing, with recorded/mocked Google and Gemini responses (never hit real APIs in CI)

## Folder structure

```
backend/
├── CLAUDE.md
├── app/
│   ├── main.py                      ← FastAPI app, router mounting, startup (scheduler init)
│   ├── core/
│   │   ├── config.py                ← settings from env, per-tenant config
│   │   ├── security.py              ← JWT verification, role/tenant authorization dependency
│   │   └── crypto.py                ← Fernet encrypt/decrypt for the tenant vault
│   ├── api/routes/
│   │   ├── clients.py
│   │   ├── sessions.py
│   │   ├── drafts.py                ← GET pending, POST approve, POST reject
│   │   ├── scorecards.py
│   │   ├── metrics.py
│   │   ├── admin.py                 ← tenants, reminder_rules, prompt_templates, users
│   │   └── webhooks.py              ← receives Apps Script Drive/Calendar pings
│   ├── integrations/
│   │   └── google/
│   │       ├── auth.py              ← per-tenant OAuth token refresh, vault read/write
│   │       ├── calendar.py
│   │       ├── drive.py
│   │       ├── gmail.py
│   │       └── tasks.py
│   ├── ai/
│   │   └── gemini_client.py
│   ├── services/
│   │   ├── calendar_scanner.py      ← naming-convention match + working-day lead-time calc
│   │   ├── transcript_normalizer.py ← Plaud text / Gemini Meet transcript → common schema
│   │   ├── context_builder.py       ← assembles client profile + Context Library slice + prior sessions of same type
│   │   ├── scorecard_generator.py   ← post-session ICF/GROW critique, grounded + structured output
│   │   ├── draft_generator.py       ← client-facing email/questionnaire drafts, tenant-tagged
│   │   └── reminder_engine.py       ← the scheduled job that triggers phases A/C/D/E at the right lead time
│   ├── models/                      ← Pydantic request/response schemas
│   ├── db/
│   │   ├── schema.sql               ← source of truth DDL (see below)
│   │   └── repository.py            ← thin data-access layer, one function per table per operation
│   └── jobs/
│       └── scheduler.py             ← APScheduler jobs: calendar poll (e.g. every 15 min), reminder check (hourly)
└── tests/
```

## Core workflows, mapped to code

**1. Calendar scanning.** `services/calendar_scanner.py` runs on a schedule (or reacts to an Apps Script webhook hit) per tenant, pulls upcoming events via `integrations/google/calendar.py`, and matches each against the five naming strings. A match is turned into (or updates) a `sessions` row with `type`, `tenant_id`, and the computed trigger date (event date minus the type's working-day lead time — working-day math must skip weekends, so don't use naive `timedelta`). An event that matches nothing is written to an `unmatched_events` table for the frontend's exception-handling UI instead of being silently dropped.

**2. Transcript ingestion.** Apps Script (see `infra/apps-script/`) watches one Drive "Inbox" folder per tenant and POSTs to `POST /webhooks/drive` with the file id and tenant on any new file (both a manual Plaud export and an auto-saved Gemini Meet transcript land here). The handler downloads the file, tags it with `source` (`plaud` or `gemini_meet` — infer from file type/naming, Gemini Meet exports are more structured), files it into the matching client's Transcripts subfolder via `integrations/google/drive.py`, and hands it to `transcript_normalizer.py`.

**3. Normalization.** `transcript_normalizer.py` converts whatever shape the source hands back into one schema: a list of `{speaker, timestamp, text}`. Use the calendar event's attendee list as ground truth to resolve generic speaker labels to the actual coach/coachee names where the source doesn't already provide them. Store both the raw file reference and the normalized text in the `transcripts` table with a `parse_status` (`ok` / `partial` / `failed`) — never let a partial parse silently block the pipeline; log it and still attempt generation with a clear "unverified transcript" flag carried into the draft.

**4. Context assembly + Gemini.** `context_builder.py` queries: the client's profile, the relevant slice of `context_library_current` (ICF competencies + GROW model docs, plus the client's own coaching profile), and prior `sessions` **of the same type only** — a 1-on-1 draft must never pull strategic-council history and vice versa. `draft_generator.py`/`scorecard_generator.py` fetch the matching `(session_type, phase)` prompt via `db/repository.py`'s `get_current_prompt_template` — both `context_library` and `prompt_templates` are append-only tables (an edit posts a new version rather than overwriting; the `_current` view exposes just the latest per `entry_group_id`) managed from the Admin tab's Context Library and Prompt Template editors. That resolved template body is handed to `gemini_client.py`, requesting structured JSON output (not free text) for anything that becomes a scorecard, so the frontend can render it deterministically rather than parsing prose.

**5. Scorecards and drafts.** `scorecard_generator.py` produces the internal-only ICF/GROW critique (never approval-gated — it's internal). `draft_generator.py` produces every client-facing artifact (reminder, summary, questionnaire, prep email), always stamped with the session's `tenant_id`, always written to `ai_drafts` with `status = pending`. Nothing in this service ever calls Gmail directly.

**6. Approval and send.** `POST /api/drafts/{id}/approve` is the **only** code path allowed to call `integrations/google/gmail.py`. It re-reads the draft's `tenant_id`, fetches that tenant's credentials from the vault, sends from that tenant's Gmail identity, and marks the draft `sent`. `POST /api/drafts/{id}/reject` records a reason (feeds the "draft approval rate" metric) and does not send. Scorecard action items are pushed to `integrations/google/tasks.py` at scorecard-generation time, independent of the email approval flow.

**7. Reminder engine.** `reminder_engine.py` runs hourly, checks `sessions` whose computed trigger date is now, and kicks off context assembly + draft generation for that session — this is what actually fires phases A, C, D, and E at the right moment. If the linked calendar event's time changes after a job was scheduled, re-run the calendar scanner diff and cancel/reschedule rather than sending a stale prep package.

## Multi-tenant credential vault

`tenants` table: `id`, `workspace_domain`, `encrypted_refresh_token`, `client_id`, `client_secret_ref` (or a secrets-manager reference, not the raw secret in the DB). `integrations/google/auth.py` is the only module that decrypts a token, and it does so per-request, never caching a decrypted token beyond the request lifecycle. A failed refresh for one tenant must not affect the other's scheduled jobs — wrap each tenant's job iteration in its own try/except and log+alert rather than raising.

## Auth and authorization

Every route depends on a `get_current_user` dependency in `core/security.py` that verifies the Supabase JWT against Supabase's JWKS (no shared secret), then loads the user's role and assigned clients from `users`. A second dependency, `require_admin`, gates admin-only routes. For `general` users, every service function that touches a `client_id` must check it against that user's assigned clients — do this in the repository layer (`db/repository.py`), not just in the route handler, so a new route can't accidentally skip the check.

## Data model (Supabase / Postgres — `db/schema.sql` is the source of truth)

| Table | Key columns |
|---|---|
| `tenants` | `id`, `workspace_domain`, `encrypted_refresh_token`, `client_id` |
| `clients` | `id`, `name`, `coach_user_id`, `tenant_id`, `drive_folder_id`, `session_types` (array) |
| `sessions` | `id`, `client_id`, `type` (`one_on_one`/`quarterly_review`/`annual_review`/`monthly_council`), `tenant_id`, `event_date`, `trigger_date`, `transcript_id`, `status` |
| `unmatched_events` | `id`, `tenant_id`, `raw_event_summary`, `event_date`, `resolved_session_type` (nullable) |
| `transcripts` | `id`, `file_ref`, `source` (`plaud`/`gemini_meet`), `normalized_text`, `parse_status` |
| `context_library` | `id`, `entry_group_id`, `client_id` (nullable = org-wide), `title` (required heading), `body`, `version` — append-only, edits insert a new row under the same `entry_group_id`; `context_library_current` view exposes the latest per group |
| `scorecards` | `id`, `session_id`, `structured_critique` (jsonb), `citations` (jsonb) |
| `ai_drafts` | `id`, `session_id`, `draft_type`, `tenant_id`, `body`, `status` (`pending`/`sent`/`rejected`), `rejection_reason` |
| `reminder_rules` | `session_type`, `lead_time_working_days`, `naming_pattern` |
| `prompt_templates` | `id`, `entry_group_id`, `session_type`, `phase` (`pre`/`post`), `title`, `body`, `version` — same append-only shape as `context_library`; `prompt_templates_current` is what generation actually reads |
| `tasks_sync` | `scorecard_id`, `google_task_id` |
| `metrics_log` | `id`, `session_id`, `gemini_tokens`, `gemini_latency_ms`, `gemini_cost_usd` |
| `users` | `id` (= Supabase Auth id), `role` (`admin`/`general`), `assigned_client_ids` (array) |

## Environment variables

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWKS_URL=                    # for JWT verification
GEMINI_API_KEY=
TOKEN_VAULT_ENCRYPTION_KEY=           # Fernet key, rotate via a documented runbook, not ad hoc
GOOGLE_OAUTH_CLIENT_ID_TENANT_A=
GOOGLE_OAUTH_CLIENT_SECRET_TENANT_A=
GOOGLE_OAUTH_CLIENT_ID_TENANT_B=
GOOGLE_OAUTH_CLIENT_SECRET_TENANT_B=
APPS_SCRIPT_WEBHOOK_SHARED_SECRET=    # verify incoming webhook calls aren't spoofed
APP_BASE_URL=
```

## API surface (summary — see `api/routes/` for full request/response schemas)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/clients` | List clients (scoped by role) |
| GET | `/api/sessions` | Upcoming + past sessions, filterable by client/type/tenant |
| GET | `/api/drafts?status=pending` | The Approvals inbox feed |
| POST | `/api/drafts/{id}/approve` | Send via the correct tenant's Gmail, mark `sent` |
| POST | `/api/drafts/{id}/reject` | Mark `rejected` with a reason |
| GET | `/api/scorecards/{session_id}` | Structured critique + citations |
| GET | `/api/metrics` | Aggregated KPIs for the Metrics view |
| GET/PUT | `/api/admin/reminder-rules` | Lead time + naming pattern per session type |
| GET | `/api/admin/prompt-templates` | Current (latest-version) prompt templates — the Obsidian-replacement prompt library, and the live source draft/scorecard generation reads |
| GET | `/api/admin/prompt-templates/{entry_group_id}/history` | All versions of one prompt template, newest first |
| POST | `/api/admin/prompt-templates` | Create a prompt template for a `(session_type, phase)` slot that doesn't have one yet |
| POST | `/api/admin/prompt-templates/{entry_group_id}/versions` | Post a new version (append-only — never overwrites) |
| GET | `/api/admin/context-library?client_id=` | Current Context Library entries, optionally scoped to a client (org-wide entries always included) |
| GET | `/api/admin/context-library/{entry_group_id}/history` | All versions of one entry, newest first |
| POST | `/api/admin/context-library` | Create a Context Library entry (org-wide or client-specific) |
| POST | `/api/admin/context-library/{entry_group_id}/versions` | Post a new version (append-only — never overwrites) |
| GET/POST | `/api/admin/tenants` | Tenant connection status (never returns raw tokens) |
| POST | `/webhooks/drive` | Apps Script → new file in a tenant's Inbox folder |
| POST | `/webhooks/calendar` | Apps Script → calendar changed (optional, if not purely polling) |

## Testing notes

Mock every Google and Gemini call in unit tests (`unittest.mock` or `respx` for HTTP-level mocking) — CI must never make a live call to either. Write at least one integration test per workflow phase (A–E) that exercises calendar-match → context-build → draft-generate end to end against fixtures, since these five phases are the actual product and a regression there is a regression the coach will notice immediately.
