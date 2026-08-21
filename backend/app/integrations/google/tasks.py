from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.google.auth import get_tenant_credentials


async def create_task(tenant_id: str, title: str, notes: str, due: str | None = None) -> str:
    """Pushes a scorecard action item to Google Tasks — fired at
    scorecard-generation time, independent of the email approval flow
    (backend/CLAUDE.md, phase 6)."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("tasks", "v1", credentials=credentials)

    body = {"title": title, "notes": notes}
    if due:
        body["due"] = due

    response = service.tasks().insert(tasklist="@default", body=body).execute()
    return response["id"]
