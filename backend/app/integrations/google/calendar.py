from datetime import UTC, datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.google.auth import get_tenant_credentials


async def list_upcoming_events(tenant_id: str, horizon_days: int = 60) -> list[dict[str, Any]]:
    """Pulls upcoming Calendar events for a tenant. Called by
    services/calendar_scanner.py, which matches each event's summary against
    the five naming strings and computes trigger dates via working-day math."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("calendar", "v3", credentials=credentials)

    now = datetime.now(UTC)
    time_max = now + timedelta(days=horizon_days)
    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return response.get("items", [])
