from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.client import Client
from app.services import calendar_scanner
from app.services.calendar_scanner import add_working_days, match_session_type
from app.session_types_generated import SessionType


def test_add_working_days_skips_weekend():
    # Friday 2026-08-21 minus 3 working days -> Tuesday 2026-08-18
    start = datetime(2026, 8, 21, tzinfo=UTC)
    result = add_working_days(start, 3)
    assert result.date().isoformat() == "2026-08-18"


def test_add_working_days_spans_two_weekends():
    # Monday 2026-08-24 minus 10 working days -> Monday 2026-08-10
    start = datetime(2026, 8, 24, tzinfo=UTC)
    result = add_working_days(start, 10)
    assert result.date().isoformat() == "2026-08-10"


def test_match_one_on_one_prefix():
    assert match_session_type("Grow Executive Coaching Jane Doe") == SessionType.ONE_ON_ONE


def test_match_exact_naming_strings():
    assert match_session_type("Grow Quarterly Strategic Review") == SessionType.QUARTERLY_REVIEW
    assert match_session_type("Grow Annual Strategic Review") == SessionType.ANNUAL_REVIEW
    assert match_session_type("Grow Monthly Strategic Council") == SessionType.MONTHLY_COUNCIL


def test_unmatched_event_returns_none():
    assert match_session_type("Random team standup") is None


def _event(event_id: str, summary: str, *emails: str) -> dict:
    return {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": "2026-10-05T10:00:00+00:00"},
        "attendees": [{"email": e} for e in emails],
    }


@pytest.mark.asyncio
async def test_scan_attributes_only_unambiguous_one_on_ones():
    jane = Client(id=uuid4(), name="Jane", email="jane@example.com", coach_user_id=uuid4(), tenant_id="tenant_a")
    sam = Client(id=uuid4(), name="Sam", email="sam@example.com", coach_user_id=uuid4(), tenant_id="tenant_a")
    events = [
        _event("e1", "Grow Executive Coaching Jane", "coach@grow.co.za", "jane@example.com"),
        _event("e2", "Grow Quarterly Strategic Review", "jane@example.com"),
        _event("e3", "Grow Executive Coaching Jane and Sam", "jane@example.com", "sam@example.com"),
    ]
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.execute.return_value.data = []

    with (
        patch.object(calendar_scanner, "get_supabase", return_value=supabase),
        patch.object(calendar_scanner, "list_clients_for_tenant", new=AsyncMock(return_value=[jane, sam])),
        patch.object(calendar_scanner, "list_upcoming_events", new=AsyncMock(return_value=events)),
    ):
        await calendar_scanner.scan_tenant("tenant_a")

    upserts = [
        (call_table.args[0], upsert.args[0])
        for call_table, upsert in zip(
            supabase.table.call_args_list[1:], supabase.table.return_value.upsert.call_args_list, strict=True
        )
    ]
    sessions = [row for table, row in upserts if table == "sessions"]
    unmatched = [row for table, row in upserts if table == "unmatched_events"]
    assert len(sessions) == 1
    assert sessions[0]["client_id"] == str(jane.id)
    assert sessions[0]["external_event_id"] == "e1"
    # The quarterly review (maybe a team) and the two-coachee 1-on-1 go to the queue.
    assert [row["raw_event_summary"] for row in unmatched] == [
        "Grow Quarterly Strategic Review",
        "Grow Executive Coaching Jane and Sam",
    ]
