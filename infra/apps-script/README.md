# Apps Script projects (one per Google Workspace tenant)

Two independent `clasp` projects — `tenant-a/` and `tenant-b/` — never one
project shared across tenants. Each holds its own `Config.gs` with that
tenant's Drive Inbox folder id and the shared webhook secret.

## Deploy

```bash
npm install -g @google/clasp
clasp login

cd infra/apps-script/tenant-a
clasp create --type standalone --title "CoachFlow Watcher — Tenant A"
clasp push
# then open the Apps Script editor and run installTriggers() once
```

Repeat for `tenant-b/`. Update `BACKEND_WEBHOOK_BASE_URL` and
`WEBHOOK_SHARED_SECRET` in each `Config.gs` to match the backend's
`APP_BASE_URL` and `APPS_SCRIPT_WEBHOOK_SHARED_SECRET` env vars before pushing.
