import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.google.auth import get_tenant_credentials


async def send_email(tenant_id: str, to: str, subject: str, body: str) -> str:
    """The only place a Gmail send should ever originate — called exclusively
    from POST /api/drafts/{id}/approve per backend/CLAUDE.md. Sends from the
    Gmail identity belonging to `tenant_id`, which the caller must have
    re-read from the draft row (never inferred or defaulted)."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("gmail", "v1", credentials=credentials)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    response = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return response["id"]
