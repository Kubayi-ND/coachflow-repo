/**
 * Per-tenant configuration. Mirrors tenant-a/Config.gs with tenant B's values.
 * Deploy independently via `clasp push` from this folder.
 */
const TENANT_ID = 'tenant_b';
const INBOX_FOLDER_ID = 'REPLACE_WITH_TENANT_B_DRIVE_INBOX_FOLDER_ID';
const BACKEND_WEBHOOK_BASE_URL = 'https://REPLACE_WITH_BACKEND_HOST';
const WEBHOOK_SHARED_SECRET = 'REPLACE_WITH_APPS_SCRIPT_WEBHOOK_SHARED_SECRET';
