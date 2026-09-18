from uuid import uuid4

from app.models.client import Client as ClientModel
from app.services.client_matching import match_client_by_attendee_email, match_client_by_name


def _client(name: str, email: str = "client@example.com") -> ClientModel:
    return ClientModel(
        id=uuid4(),
        name=name,
        email=email,
        coach_user_id=uuid4(),
        tenant_id="tenant_a",
        drive_folder_id=None,
        session_types=[],
    )


def test_match_client_by_name_is_case_and_whitespace_insensitive():
    clients = [_client("Jane Doe")]
    assert match_client_by_name(clients, "  jane doe  ") is not None
    assert match_client_by_name(clients, "Someone Else") is None


def test_match_client_by_attendee_email_is_case_insensitive():
    clients = [_client("Jane Doe", email="jane@example.com")]
    event = {"attendees": [{"email": "coach@example.com"}, {"email": "Jane@Example.com"}]}
    assert match_client_by_attendee_email(clients, event) is not None
    assert match_client_by_attendee_email(clients, {"attendees": []}) is None


def test_duplicate_names_are_ambiguous_not_first_match():
    clients = [_client("Jane Doe", "jane1@example.com"), _client("Jane Doe", "jane2@example.com")]
    assert match_client_by_name(clients, "Jane Doe") is None


def test_several_known_clients_on_one_event_is_ambiguous():
    # A team session with two coachees on the invite must never be attributed
    # to whichever client happens to come first.
    clients = [_client("Jane Doe", "jane@example.com"), _client("Sam Lee", "sam@example.com")]
    event = {"attendees": [{"email": "jane@example.com"}, {"email": "sam@example.com"}]}
    assert match_client_by_attendee_email(clients, event) is None
