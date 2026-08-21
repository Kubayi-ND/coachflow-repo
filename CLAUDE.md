# CoachFlow — Monorepo Guide (root)

> Scope note: this repo implements the **Google Workspace-only** iteration of the CoachFlow design (no Microsoft/Teams integration). Two Google Workspace tenants are still in scope — this is multi-tenant within Google, not single-tenant. If Microsoft support is added later, it slots in as a third tenant row and a new `integrations/microsoft` package in the backend; nothing here needs to be rewritten for that.

## What this project is

CoachFlow is an internal tool for an executive coaching practice that replaces a manual, multi-tool workflow (Plaud recorder → Google Drive → Gemini Notebook → Obsidian prompts → manual email) with one system. It watches Google Calendar for five recurring session types, ingests meeting transcripts (Plaud exports and Gemini Meet's auto-captured transcripts), builds AI-assembled prep and post-session evaluations grounded in a coaching Context Library (ICF competencies + GROW model), and drafts every client-facing communication — but never sends anything without the coach approving it first in a dashboard inbox.

Read `frontend/CLAUDE.md` and `backend/CLAUDE.md` before working in either package — they contain the technical detail this file only summarizes.

## Monorepo structure

```
coachflow/
├── CLAUDE.md                  ← this file
├── frontend/                  ← React dashboard (see frontend/CLAUDE.md)
│   └── CLAUDE.md
├── backend/                   ← Python orchestrator + API (see backend/CLAUDE.md)
│   └── CLAUDE.md
├── shared/
│   └── types/                 ← OpenAPI-generated TS types, shared enums (session types, roles)
├── infra/
│   ├── docker-compose.yml     ← local dev: backend + Postgres (or Supabase local) + Redis (if job queue used)
│   └── apps-script/           ← the two small Apps Script projects (one per Google tenant)
│       ├── tenant-a/
│       └── tenant-b/
├── docs/                      ← architecture write-ups (source of truth for business logic — keep in sync with this repo)
└── .github/workflows/         ← CI: lint, typecheck, test, build, per package
```

Package manager: **pnpm** for the frontend (with a workspace at the repo root if more JS packages are added later), **uv** or **poetry** for the backend's Python environment. Keep frontend and backend as independently deployable services — the frontend never talks to Google APIs or Supabase's service-role key directly; it only talks to the backend's REST API and to Supabase Auth (for login/session only).

## Tech stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Fast dev loop, no framework lock-in for a dashboard-shaped app |
| Auth | Supabase Auth | Handles admin/general-user login and issues the JWT both frontend and backend trust |
| App database | Supabase (Postgres) | Structured store for clients, sessions, drafts, scorecards, reminder rules — Drive stays the document store, Supabase stays the state store |
| Backend | Python 3.11+ / FastAPI | Async-friendly, typed, good fit for orchestrating Google APIs + Gemini calls |
| AI | Gemini API (`google-generativeai`) | Replaces Gemini Notebook — called on demand with assembled context, not manual paste-and-chat |
| Automation | Google Apps Script | Cheapest place to run a Drive watch-folder trigger and Calendar polling, native to each Workspace tenant |
| Google integrations | Calendar, Drive, Gmail, Tasks APIs (`google-api-python-client`) | Session triggers, transcript filing, tenant-correct sending, action-item sync |

## Cross-cutting concerns

**Auth flow.** Supabase Auth issues a JWT on login (frontend uses `@supabase/supabase-js`). The frontend attaches that JWT as a Bearer token on every backend request. The backend verifies it against Supabase's JWKS endpoint (no shared secret to manage) and reads the user's role and assigned clients from the `users` table before authorizing the request. There is no separate backend session — the JWT is the only credential the frontend holds.

**Multi-tenant model (Google-only, still 2 tenants).** Every `clients`, `sessions`, and `ai_drafts` row carries a `tenant_id` (`tenant_a` / `tenant_b`). The backend's tenant credential vault holds one OAuth token set per tenant; every Google API call is made with the credentials matching the record's `tenant_id`, and the send step reads that id back rather than re-deriving it, so a Tenant B client can never be emailed from Tenant A's Gmail identity.

**Session types are a shared enum** — define it once (`shared/types` or a single Python/TS constants file, generated from one source) and reference it from both packages rather than re-typing the naming strings:

| Type | Calendar naming string | Lead time |
|---|---|---|
| `one_on_one` | `Grow Executive Coaching [Coachee Name]` | 3 working days |
| `quarterly_review` | `Grow Quarterly Strategic Review` | 5 working days |
| `annual_review` | `Grow Annual Strategic Review` | 10 working days |
| `monthly_council` | `Grow Monthly Strategic Council` | 5 working days |

**Roles.** `admin` manages tenants, clients, the Context Library, prompt templates, and reminder rules. `general` (the coach) works within assigned clients, reviews the Approvals inbox, and reviews scorecards. Enforce this in the backend service layer (don't rely on the frontend hiding UI as the only gate) — see `backend/CLAUDE.md` for the exact authorization pattern.

**Human-in-the-loop is non-negotiable.** Every client-facing draft (reminder, summary, questionnaire, prep email) is written to `ai_drafts` with `status = pending` and is only sent after an explicit approve action from the dashboard. No code path should call the Gmail send endpoint except the approval handler.

## Local development

1. `docker compose -f infra/docker-compose.yml up` — brings up a local Postgres (or point at a Supabase project) and Redis if the backend uses a job queue for scheduled polling.
2. `cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000`
3. `cd frontend && pnpm install && pnpm dev` (proxies `/api` to `localhost:8000` in `vite.config.ts`)
4. Google API access in local dev uses a sandbox/test Workspace tenant with its own OAuth client — never point local dev at the real coach's calendars.

## Deployment targets (suggested)

Frontend → Vercel or Netlify (static build). Backend → a container platform with cron/scheduler support (Cloud Run + Cloud Scheduler, or Fly.io + its scheduled machines). Supabase stays hosted. Apps Script projects deploy independently per tenant via `clasp`.

## Where the business logic comes from

This repo implements the design in `docs/` (the CoachFlow architecture write-up). If a requirement here and in `docs/` ever disagree, treat `docs/` as the spec and file a note rather than silently picking one — the reminder lead times and naming conventions in particular came directly from the client's brief and shouldn't be adjusted without confirming with them first.
