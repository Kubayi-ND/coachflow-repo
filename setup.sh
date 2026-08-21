#!/usr/bin/env bash
# One-time local dev bootstrap for CoachFlow (see root CLAUDE.md "Local development").
# Run from the repo root: ./setup.sh
# Idempotent — safe to re-run after pulling new dependencies.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { printf '\n\033[1;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mWARN:\033[0m %s\n' "$1" >&2; }
missing=0

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    warn "$1 not found — $2"
    missing=1
  fi
}

log "Checking required tools"
require uv "install from https://docs.astral.sh/uv/getting-started/installation/ (backend Python env + deps)"
require node "install Node 20+ from https://nodejs.org/ (frontend)"
if [ "$missing" = "1" ]; then
  warn "Install the missing tools above, then re-run ./setup.sh"
  exit 1
fi

PKG_MGR="npm"
if command -v pnpm >/dev/null 2>&1; then
  PKG_MGR="pnpm"
else
  warn "pnpm not found (root CLAUDE.md specifies pnpm for the frontend) — falling back to npm."
  warn "Install pnpm (npm install -g pnpm) for a lockfile that matches CI."
fi

log "Backend: syncing Python environment (uv sync)"
(cd backend && uv sync --all-extras)

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  log "Created backend/.env from .env.example — fill in Supabase/Gemini/Google OAuth values before running the API"
else
  log "backend/.env already exists, leaving it alone"
fi

log "Frontend: installing dependencies ($PKG_MGR install)"
(cd frontend && "$PKG_MGR" install)

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
  log "Created frontend/.env from .env.example — fill in Supabase URL/anon key before running the app"
else
  log "frontend/.env already exists, leaving it alone"
fi

log "Generating shared session-type constants"
node --experimental-strip-types shared/types/scripts/generate-session-types.ts
python3 shared/types/scripts/generate_session_types.py 2>/dev/null \
  || (cd backend && uv run python ../shared/types/scripts/generate_session_types.py)

cat <<'EOF'

Setup complete. Next steps:

  1. Fill in backend/.env and frontend/.env with real credentials
     (Supabase project, Gemini API key, per-tenant Google OAuth client).
  2. Bring up local infra:      docker compose -f infra/docker-compose.yml up
  3. Run the backend:           cd backend && uv run uvicorn app.main:app --reload --port 8000
  4. Run the frontend:          cd frontend && pnpm dev   (or npm run dev)

Local dev must point at a sandbox/test Workspace tenant for Google API access —
never the real coach's calendars (root CLAUDE.md).
EOF
