"""Naming-convention match + working-day lead-time calc (backend/CLAUDE.md phase 1).

Runs on a schedule (jobs/scheduler.py) or reacts to the /webhooks/calendar hit
from Apps Script. An event that matches nothing is written to
unmatched_events instead of being silently dropped, so the frontend's
Calendar view can surface it for the coach to assign manually.
"""
from datetime import datetime, timedelta
from typing import Any

from app.db.repository import get_supabase, list_clients_for_tenant, rows_of
from app.integrations.google.calendar import list_upcoming_events
from app.services.client_matching import AUTO_MATCHED_SESSION_TYPES, match_client_by_attendee_email
from app.session_types_generated import SESSION_TYPES, SessionType

# One-on-ones are the only naming pattern with a variable slot ("[Coachee Name]"),
# so they're matched as a prefix; the other three are matched exactly.
_ONE_ON_ONE_PREFIX = "Grow Executive Coaching"


def add_working_days(start: datetime, working_days: int) -> datetime:
    """Adds N *working* days (Mon-Fri) to start, skipping weekends. Must match
    frontend/src/lib/workingDays.ts exactly — both compute the same
    trigger/countdown dates from the same inputs."""
    current = start
    remaining = working_days
    step = timedelta(days=1)
    while remaining > 0:
        current -= step
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            remaining -= 1
    return current


def match_session_type(event_summary: str) -> SessionType | None:
    summary = event_summary.strip()
    if summary.startswith(_ONE_ON_ONE_PREFIX):
        return SessionType.ONE_ON_ONE
    for session_type, definition in SESSION_TYPES.items():
        if session_type == SessionType.ONE_ON_ONE:
            continue
        if summary == definition.naming_pattern:
            return session_type
    return None


async def scan_tenant(tenant_id: str) -> None:
    supabase = get_supabase()
    reminder_rules = {
        row["session_type"]: row["lead_time_working_days"]
        for row in rows_of(supabase.table("reminder_rules").select("*").execute())
    }

    clients = await list_clients_for_tenant(tenant_id)
    events = await list_upcoming_events(tenant_id)
    for event in events:
        summary = event.get("summary", "")
        start_raw = event["start"].get("dateTime") or event["start"].get("date")
        event_date = datetime.fromisoformat(start_raw)

        session_type = match_session_type(summary)
        # Only 1-on-1s are attributed automatically, and only to exactly one
        # client on the attendee list; anything else (unknown title, a
        # quarterly/annual/monthly session that may be a team, D-08, or an
        # ambiguous attendee list) goes to the coach's unmatched queue.
        client = (
            match_client_by_attendee_email(clients, event)
            if session_type in AUTO_MATCHED_SESSION_TYPES
            else None
        )
        if session_type is None or client is None or not event.get("id"):
            _file_unmatched(supabase, tenant_id, summary, event_date)
            continue

        lead_time = reminder_rules.get(session_type.value, SESSION_TYPES[session_type].lead_time_working_days)
        trigger_date = add_working_days(event_date, lead_time)

        # Keyed on the calendar event id, so a rescheduled event updates its
        # own session and two clients' sessions at the same time never merge.
        supabase.table("sessions").upsert(
            {
                "client_id": str(client.id),
                "type": session_type.value,
                "tenant_id": tenant_id,
                "event_date": event_date.isoformat(),
                "trigger_date": trigger_date.isoformat(),
                "status": "upcoming",
                "external_event_id": event["id"],
            },
            on_conflict="external_event_id",
        ).execute()


def _file_unmatched(supabase: Any, tenant_id: str, summary: str, event_date: datetime) -> None:
    supabase.table("unmatched_events").upsert(
        {
            "tenant_id": tenant_id,
            "raw_event_summary": summary,
            "event_date": event_date.isoformat(),
        },
        on_conflict="tenant_id,raw_event_summary,event_date",
    ).execute()
