"""Naming-convention match + working-day lead-time calc (backend/CLAUDE.md phase 1).

Runs on a schedule (jobs/scheduler.py) or reacts to the /webhooks/calendar hit
from Apps Script. An event that matches nothing is written to
unmatched_events instead of being silently dropped, so the frontend's
Calendar view can surface it for the coach to assign manually.
"""
from datetime import datetime, timedelta

from app.db.repository import get_supabase, rows_of
from app.integrations.google.calendar import list_upcoming_events
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

    events = await list_upcoming_events(tenant_id)
    for event in events:
        summary = event.get("summary", "")
        start_raw = event["start"].get("dateTime") or event["start"].get("date")
        event_date = datetime.fromisoformat(start_raw)

        session_type = match_session_type(summary)
        if session_type is None:
            supabase.table("unmatched_events").upsert(
                {
                    "tenant_id": tenant_id,
                    "raw_event_summary": summary,
                    "event_date": event_date.isoformat(),
                },
                on_conflict="tenant_id,raw_event_summary,event_date",
            ).execute()
            continue

        lead_time = reminder_rules.get(session_type.value, SESSION_TYPES[session_type].lead_time_working_days)
        trigger_date = add_working_days(event_date, lead_time)

        # Client resolution (matching the coachee name / attendees to a `clients`
        # row) happens against calendar attendees; omitted here as it depends on
        # how each tenant records client identity in the event body — wire this
        # to the client directory lookup once that convention is finalized.
        supabase.table("sessions").upsert(
            {
                "type": session_type.value,
                "tenant_id": tenant_id,
                "event_date": event_date.isoformat(),
                "trigger_date": trigger_date.isoformat(),
                "status": "upcoming",
            },
            on_conflict="tenant_id,type,event_date",
        ).execute()
