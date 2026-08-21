# CoachFlow — Quick Setup

Two independently deployable packages: a Python/FastAPI backend and a React/Vite
frontend. See root `CLAUDE.md` for the full architecture; this file is just the
fastest path to a running local environment.

## Prerequisites

| Tool | Used for | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Backend Python env + deps | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node 20+ | Frontend build/dev server | https://nodejs.org/ |
| [pnpm](https://pnpm.io/installation) | Frontend package manager (project standard) | `npm install -g pnpm` |
| Docker (optional) | Local Postgres/Redis instead of hosted Supabase | https://docs.docker.com/get-docker/ |

## One-command setup

From the repo root:

```bash
./setup.sh
```

This syncs the backend's Python env, installs frontend dependencies, copies
`.env.example` → `.env` for both packages (only if the `.env` doesn't already
exist — it will never overwrite credentials you've already filled in), and
regenerates the shared session-type constants. Re-run it any time after
pulling new dependencies; it's idempotent.

If you'd rather do it by hand, or `setup.sh` isn't available on your shell,
the two packages below are independent — set up whichever one you're touching.

## Backend

```bash
cd backend
uv sync --all-extras
cp .env.example .env   # then fill in the values below
uv run uvicorn app.main:app --reload --port 8000
```

Fill in `backend/.env`:

| Variable | Where it comes from |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWKS_URL` | Your Supabase project settings (use a sandbox project for local dev, not the real one) |
| `GEMINI_API_KEY` | Google AI Studio / Gemini API key |
| `TOKEN_VAULT_ENCRYPTION_KEY` | A Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GOOGLE_OAUTH_CLIENT_ID_TENANT_A/B`, `GOOGLE_OAUTH_CLIENT_SECRET_TENANT_A/B` | One OAuth client per Workspace tenant, from a **sandbox/test tenant** — never the real coach's calendars (root `CLAUDE.md`) |
| `APPS_SCRIPT_WEBHOOK_SHARED_SECRET` | Any random string; must match the same value in each `infra/apps-script/tenant-*/Config.gs` |
| `APP_BASE_URL` | `http://localhost:8000` for local dev |

Verify it's up: `curl http://localhost:8000/healthz` → `{"status":"ok"}`

Checks (also run in CI):

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```

## Frontend

```bash
cd frontend
pnpm install
cp .env.example .env   # then fill in the values below
pnpm dev
```

Fill in `frontend/.env`:

| Variable | Where it comes from |
|---|---|
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Same Supabase project as the backend — anon key, not service role |
| `VITE_API_BASE_URL` | `http://localhost:8000` for local dev (Vite also proxies `/api` and `/webhooks` there — see `vite.config.ts`) |

Opens at `http://localhost:5173`. `pnpm dev`/`pnpm build` regenerate
`src/types/sessionTypes.generated.ts` from `shared/types/session-types.json`
automatically (`predev`/`prebuild` scripts) — don't hand-edit that file.

Checks (also run in CI):

```bash
pnpm lint
pnpm typecheck
pnpm test -- --run
pnpm build
```

E2E (Playwright, Approvals-inbox and login flows): `pnpm test:e2e`.

## Local infra (optional)

```bash
docker compose -f infra/docker-compose.yml up
```

Brings up a local Postgres seeded from `backend/app/db/schema.sql`. Use this
instead of a hosted Supabase project if you want a fully offline backend —
you'll lose Supabase Auth in that case, so it's mainly useful for backend-only
work against the schema.

## Common issues

- **Backend won't start / `pydantic` validation error on `Settings()`** — one of
  the required env vars in `backend/.env` is missing. Every field in
  `app/core/config.py`'s `Settings` is required, no defaults.
- **Frontend shows a blank page / 401s against `/api`** — check
  `VITE_API_BASE_URL` points at a running backend, and that you're logged in
  (Supabase Auth session) so `apiClient.ts` has a JWT to attach.
- **`pnpm: command not found`** — `setup.sh` falls back to `npm` automatically,
  but CI (`.github/workflows/ci.yml`) runs `pnpm install --frozen-lockfile`
  against a `pnpm-lock.yaml`; install pnpm and run `pnpm install` once before
  you push any dependency changes, so the committed lockfile matches CI.
