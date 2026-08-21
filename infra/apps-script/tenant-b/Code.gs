/**
 * Watches this tenant's Drive Inbox folder for new transcript files and pings
 * the backend on each new Calendar event, per the flow in backend/CLAUDE.md:
 * "Apps Script watches one Drive Inbox folder per tenant and POSTs to
 * POST /webhooks/drive ... on any new file." Calendar polling is the fallback
 * path when /webhooks/calendar isn't wired up; the backend's own
 * calendar_scanner job can also poll directly, so this is belt-and-suspenders.
 *
 * Install triggers once per tenant deployment:
 *   installTriggers() — run manually from the Apps Script editor after clasp push.
 */
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('pollDriveInbox').timeBased().everyMinutes(5).create();
  ScriptApp.newTrigger('pollCalendar').timeBased().everyMinutes(15).create();
}

function pollDriveInbox() {
  const props = PropertiesService.getScriptProperties();
  const lastCheckedIso = props.getProperty('LAST_DRIVE_CHECK') || new Date(0).toISOString();
  const folder = DriveApp.getFolderById(INBOX_FOLDER_ID);
  const files = folder.getFiles();
  const nowIso = new Date().toISOString();

  while (files.hasNext()) {
    const file = files.next();
    if (file.getDateCreated().toISOString() > lastCheckedIso) {
      notifyBackend('/webhooks/drive', {
        tenant_id: TENANT_ID,
        file_id: file.getId(),
        file_name: file.getName(),
        mime_type: file.getMimeType(),
      });
    }
  }
  props.setProperty('LAST_DRIVE_CHECK', nowIso);
}

function pollCalendar() {
  notifyBackend('/webhooks/calendar', { tenant_id: TENANT_ID });
}

function notifyBackend(path, payload) {
  const response = UrlFetchApp.fetch(BACKEND_WEBHOOK_BASE_URL + path, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'X-Webhook-Secret': WEBHOOK_SHARED_SECRET },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  if (response.getResponseCode() >= 300) {
    console.error('Webhook call failed: ' + path + ' -> ' + response.getContentText());
  }
}
