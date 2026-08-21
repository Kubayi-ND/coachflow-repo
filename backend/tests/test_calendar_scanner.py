from datetime import UTC, datetime

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
