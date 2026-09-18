"""Client-resolution helpers shared by every one-time backfill source —
Drive-based (services/drive_backfill.py) and local-file-based
(services/local_backfill.py) alike. Both feed these the same kind of input
(a subfolder/frontmatter name, or a calendar event's attendee list); only
where that input comes from differs between the two backfill paths.
"""
from typing import Any

from app.models.client import Client as ClientModel
from app.session_types_generated import SessionType


def match_client_by_name(clients: list[ClientModel], name: str) -> ClientModel | None:
    """Exactly one client with this name, or None — two clients sharing a name
    must go to the unmatched queue, never to whichever row comes first."""
    normalized = name.strip().casefold()
    return _only([client for client in clients if client.name.strip().casefold() == normalized])


def match_client_by_attendee_email(clients: list[ClientModel], event: dict[str, Any]) -> ClientModel | None:
    """Exactly one client on the attendee list, or None. An event with several
    known clients on it (a team session) is never attributed to one of them —
    doing so would feed that person's private history into the team's prompts
    and vice versa. Callers only use this for 1-on-1s (see
    AUTO_MATCHED_SESSION_TYPES)."""
    attendee_emails = {a.get("email", "").strip().lower() for a in event.get("attendees", [])}
    return _only([client for client in clients if client.email.strip().lower() in attendee_emails])


# Until calendar titles say who a quarterly/annual/monthly session is with
# (individual or team, docs/decisions.md D-08), only 1-on-1s are matched to a
# client automatically; everything else goes to the coach's unmatched queue.
AUTO_MATCHED_SESSION_TYPES = frozenset({SessionType.ONE_ON_ONE})


def _only(matches: list[ClientModel]) -> ClientModel | None:
    unique = {client.id: client for client in matches}
    return next(iter(unique.values())) if len(unique) == 1 else None
