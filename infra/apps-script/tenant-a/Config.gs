/**
 * Per-tenant configuration. tenant-b/Config.gs is identical except for the
 * constants below — deploy independently via `clasp push` from each folder,
 * never share one Apps Script project across tenants (that would defeat the
 * whole point of per-tenant OAuth isolation described in the root CLAUDE.md).
 */
const TENANT_ID = 'tenant_a';
const INBOX_FOLDER_ID = 'REPLACE_WITH_TENANT_A_DRIVE_INBOX_FOLDER_ID';
const BACKEND_WEBHOOK_BASE_URL = 'https://REPLACE_WITH_BACKEND_HOST';
const WEBHOOK_SHARED_SECRET = 'REPLACE_WITH_APPS_SCRIPT_WEBHOOK_SHARED_SECRET';
