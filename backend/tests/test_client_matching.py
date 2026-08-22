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
