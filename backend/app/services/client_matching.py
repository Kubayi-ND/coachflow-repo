"""Client-resolution helpers shared by every one-time backfill source —
Drive-based (services/drive_backfill.py) and local-file-based
(services/local_backfill.py) alike. Both feed these the same kind of input
(a subfolder/frontmatter name, or a calendar event's attendee list); only
where that input comes from differs between the two backfill paths.
"""
from typing import Any

from app.models.client import Client as ClientModel


def match_client_by_name(clients: list[ClientModel], name: str) -> ClientModel | None:
    normalized = name.strip().casefold()
    for client in clients:
        if client.name.strip().casefold() == normalized:
            return client
    return None


def match_client_by_attendee_email(clients: list[ClientModel], event: dict[str, Any]) -> ClientModel | None:
    attendee_emails = {a.get("email", "").strip().lower() for a in event.get("attendees", [])}
    for client in clients:
        if client.email.strip().lower() in attendee_emails:
            return client
    return None
