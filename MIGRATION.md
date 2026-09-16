# CoachFlow — Account Migration Guide

Moving this repo from a personal GitHub account to a new GitHub
organisation (work account). This guide assumes the destination already
exists: a GitHub org you have access to, and — if you're not reusing the
current ones — a new Supabase project, Gemini API key, and sandbox Google
Workspace tenant.

**The important thing to understand up front:** `git push` only moves
code. It does **not** move `.env` secrets (they're git-ignored on
purpose), Supabase project data, Google OAuth client bindings, Apps
Script deployments, or CI/deploy-platform configuration. Each of those
has to be re-pointed or re-provisioned by hand. This guide is organized
around that split.

## 1. Pre-migration checklist

Before touching git, confirm you have (or have decided on) each of these:

- [ ] Write access to the destination GitHub org
- [ ] Supabase: reusing the existing project, or a new one under the work org's Supabase account?
- [ ] Gemini API key: reusing the existing key, or a new one scoped to the work org's project (for separate billing/quota)?
- [ ] Sandbox Google Workspace tenant + OAuth clients for local/dev use (per root `CLAUDE.md`: **never point dev at the real coach's calendars**)
- [ ] Decision: rotate `TOKEN_VAULT_ENCRYPTION_KEY` during the move, or carry it over unchanged? (see §4.5 — this is the highest-risk step if you rotate it)

## 2. Repository transfer

Current remote: `origin = https://github.com/Kubayi-ND/coachflow-repo.git`
(branches: `main`, `version-control`, `claude/coachflow-ui-design-kgrbei`).

**First**, check for uncommitted work and commit or stash it — nothing
uncommitted survives a transfer:

```bash
git status
```

**Option A — GitHub "Transfer ownership" (recommended if you already own
this repo and are moving it into an org you have access to):**

GitHub → repo → Settings → scroll to "Danger Zone" → Transfer ownership.
This preserves issues, PR history, and stars, and GitHub auto-redirects
the old URL to the new one. Requires admin on the destination org.

**Option B — new repo + push history (use this if Option A isn't
available, e.g. you don't have transfer rights into the org):**

```bash
# create an empty repo under the work org first (via GitHub UI or gh cli), then:
git remote add work-origin https://github.com/Mindworx-Academy-IT/coachflow-repo.git
git push work-origin --all
git push work-origin --tags
```

**Then repoint your local `origin`:**

```bash
git remote set-url origin https://github.com/<work-org>/coachflow-repo.git
git remote -v   # verify
```

If you used Option B, remove the now-redundant `work-origin` remote:
`git remote remove work-origin`.

## 3. What travels automatically vs. what doesn't

| Travels with `git push` | Does NOT travel — see §4 |
|---|---|
| All source code (`backend/`, `frontend/`, `shared/`) | `.env` files (git-ignored) |
| `.env.example` files (safe, no real values) | Supabase project + data |
| `.github/workflows/ci.yml` | Gemini API key |
| `docs/`, `CLAUDE.md` files, `SETUP.md` | Google OAuth client credentials |
| `infra/docker-compose.yml`, `infra/apps-script/**/*.gs` source | `infra/apps-script/**/.clasp.json` (git-ignored, per-machine auth) |
| | Deploy platform (Vercel/Netlify/Cloud Run) project bindings |
| | GitHub org-level settings (branch protection, required checks) |

## 4. Manual steps — external bindings

### 4.1 `.env` files

`backend/.env` and `frontend/.env` are git-ignored and were never
committed — they don't exist in the new repo. Recreate them from the
tracked `.env.example` files:

```bash
cd backend && cp .env.example .env    # then fill in values below
cd frontend && cp .env.example .env   # then fill in values below
```

**`backend/.env`** (see `backend/CLAUDE.md` for the full data-model
context behind each):

| Variable | Notes |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWKS_URL` | From the Supabase project you decided on in §1 |
| `GEMINI_API_KEY` | From the Gemini key you decided on in §1 |
| `TOKEN_VAULT_ENCRYPTION_KEY` | See §4.5 before setting this |
| `GOOGLE_OAUTH_CLIENT_ID_TENANT_A/B`, `GOOGLE_OAUTH_CLIENT_SECRET_TENANT_A/B` | See §4.3 |
| `APPS_SCRIPT_WEBHOOK_SHARED_SECRET` | See §4.4 — must match each tenant's `Config.gs` |
| `APP_BASE_URL` | The backend's public URL in the new environment |

**`frontend/.env`**:

| Variable | Notes |
|---|---|
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Same Supabase project as the backend, anon key not service role |
| `VITE_API_BASE_URL` | Points at the backend from the new environment |

### 4.2 Supabase project

- **Reusing the existing project:** nothing to do beyond copying the same values into the new `.env` files. Consider transferring project ownership to the work org's Supabase organization if billing should move too.
- **New project:** run `backend/app/db/schema.sql` against it, then re-create the `users` table's role/`assigned_client_ids` rows, and re-seed `context_library`/`prompt_templates` (these are append-only tables — see `backend/CLAUDE.md`'s data model). Note the existing memory that the live Context Library table has been observed empty in this project before — verify what's actually populated rather than assuming the old project was fully seeded.

### 4.3 Google OAuth clients per tenant

These are bound to a Google Cloud project, not to GitHub, so they don't
need to change unless the work org wants its own Cloud project. If
reusing: just copy `GOOGLE_OAUTH_CLIENT_ID/SECRET_TENANT_A/B` into the new
`.env`. If creating new sandbox OAuth clients, follow root `CLAUDE.md`'s
rule: use a sandbox/test Workspace tenant, never the real coach's
calendars, for local/dev.

### 4.4 `APPS_SCRIPT_WEBHOOK_SHARED_SECRET`

This value must be identical in `backend/.env` and in **each**
`infra/apps-script/tenant-a/Config.gs` / `tenant-b/Config.gs`. If you
rotate it, update both sides together — a mismatch fails silently as a
401 on the webhook, not an obvious startup error.

### 4.5 `TOKEN_VAULT_ENCRYPTION_KEY` (highest-risk step)

This Fernet key encrypts each tenant's OAuth refresh token at rest in the
`tenants` table (`encrypted_refresh_token`). If you **rotate** it as part
of the migration:

- Every existing `encrypted_refresh_token` becomes undecryptable with the new key.
- Either re-encrypt all rows with the new key before switching the backend over, or plan to have each tenant re-authorize (re-run the OAuth consent flow) from scratch after the switch.
- Do this in a maintenance window, not live — a coach mid-session shouldn't hit a broken send because the vault silently failed to decrypt.

If you're **not** rotating it, just copy the existing value into the new
`.env` unchanged.

### 4.6 Apps Script (clasp) deployments

`.clasp.json` per tenant project is git-ignored (it holds per-machine
auth) and won't exist after the repo move. Re-link from the new
machine/account:

```bash
npm install -g @google/clasp
clasp login

cd infra/apps-script/tenant-a
clasp create --type standalone --title "CoachFlow Watcher — Tenant A"
clasp push
# then open the Apps Script editor and run installTriggers() once
```

Repeat for `tenant-b/`. Before pushing, update `BACKEND_WEBHOOK_BASE_URL`
and `WEBHOOK_SHARED_SECRET` in each `Config.gs` to match the new
`APP_BASE_URL` and `APPS_SCRIPT_WEBHOOK_SHARED_SECRET`. Full detail in
`infra/apps-script/README.md`.

### 4.7 Deploy platform bindings

Per root `CLAUDE.md`'s suggested targets (frontend → Vercel/Netlify,
backend → Cloud Run/Fly.io): reconnect the new GitHub repo as the deploy
source in each platform's dashboard, and re-enter every env var from §4.1
there — platform env vars are also not stored in the repo.

### 4.8 CI and GitHub org settings

`.github/workflows/ci.yml` travels with the code and references no
secrets (all Google/Gemini calls are mocked in tests — see
`backend/CLAUDE.md`'s testing notes), so CI itself needs no changes
beyond the repo existing at its new location. What does **not** travel:
any branch-protection rules or required-status-checks configured in
GitHub's repo/org settings — re-create those in the new org if you had
them.

### 4.9 Data that must NOT be copied over

`.gitignore` excludes `backend/Candidates Pack/` and
`backend/data/local_backfill/**` because they contain real client names
and emails from one-off backfills. Don't copy these into the new
account's filesystem or repo as part of the migration — if that data
needs to exist in the new environment, that's a separate, deliberate
decision with its own handling, not a byproduct of a repo move.

## 5. Post-migration verification

Run through this after the new environment is wired up:

```bash
cd backend && uv sync --all-extras && uv run uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/healthz          # expect {"status":"ok"}
```

```bash
cd frontend && pnpm install && pnpm dev
# open http://localhost:5173, log in via Supabase Auth
```

- [ ] Login succeeds (confirms `SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` are correct)
- [ ] `/api/clients` and `/api/drafts?status=pending` return data, not 401s (confirms JWT verification against the new `SUPABASE_JWKS_URL`)
- [ ] Trigger a test Drive upload in each tenant's Inbox folder and confirm `POST /webhooks/drive` is received (confirms Apps Script → new `APP_BASE_URL` wiring and the shared secret match)
- [ ] Run one draft through the full Approvals-inbox loop (approve & send) in a sandbox tenant to confirm the Gmail send path and tenant credential vault both resolve correctly
- [ ] `uv run pytest` and `pnpm test -- --run` both pass in the new environment

If anything fails, check `SETUP.md`'s "Common issues" section first —
most failures at this stage are a missing/incorrect env var rather than
a code problem.

## 6. Rollback

Keep the original GitHub repo/account and the original Supabase
project/OAuth clients untouched and functioning until every item in §5
passes. Don't delete, transfer away, or de-provision anything from the
old setup until the new one is confirmed working end-to-end — the coach's
production workflow should have a working fallback for the duration of
the migration.
