"""Per-client access control: a coach only reaches the clients in
users.assigned_client_ids, through every route that exposes client data —
drafts, scorecards, sessions and the Context Library. Admins pass through.

Routes are exercised through TestClient + app.dependency_overrides (same
convention as test_clients.py); the data layer is patched at the names each
module imported, so no Supabase call is made.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user, require_coach_or_admin
from app.models.client import Client
from app.models.draft import AiDraft, DraftStatus, DraftType
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole, UserStatus
from app.session_types_generated import SessionType

CLIENT_A = uuid4()  # assigned to the coach
CLIENT_B = uuid4()  # someone else's client


def _coach() -> User:
    return User(
        id=uuid4(), email="coach@example.com", role=UserRole.GENERAL, status=UserStatus.ACTIVE,
        assigned_client_ids=[CLIENT_A],
    )


def _admin() -> User:
    return User(id=uuid4(), email="admin@example.com", role=UserRole.ADMIN, status=UserStatus.ACTIVE)


def _session(client_id) -> Session:
    now = datetime.now(UTC)
    return Session(
        id=uuid4(), client_id=client_id, type=SessionType.ONE_ON_ONE, tenant_id="tenant_a",
        event_date=now, trigger_date=now, status=SessionStatus.UPCOMING,
    )


def _draft(session: Session) -> AiDraft:
    return AiDraft(
        id=uuid4(), session_id=session.id, draft_type=DraftType.SUMMARY, tenant_id="tenant_a",
        body="Private summary", status=DraftStatus.PENDING,
    )


def _as(user: User) -> TestClient:
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_coach_or_admin] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    from app.main import app

    app.dependency_overrides.clear()


# --- Drafts -------------------------------------------------------------------


def test_draft_list_is_restricted_to_assigned_clients():
    mock_list = AsyncMock(return_value=[])
    with patch("app.api.routes.drafts.list_drafts", new=mock_list):
        assert _as(_coach()).get("/api/drafts").status_code == 200
    assert mock_list.call_args.args[0] == [CLIENT_A]


def test_admin_draft_list_is_unrestricted():
    mock_list = AsyncMock(return_value=[])
    with patch("app.api.routes.drafts.list_drafts", new=mock_list):
        _as(_admin()).get("/api/drafts")
    assert mock_list.call_args.args[0] is None


def test_coach_cannot_approve_another_clients_draft_and_nothing_is_sent():
    session = _session(CLIENT_B)
    draft = _draft(session)
    mock_send = AsyncMock()
    with (
        patch("app.api.routes.drafts.get_draft", new=AsyncMock(return_value=draft)),
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch("app.api.routes.drafts.send_email", new=mock_send),
    ):
        response = _as(_coach()).post(f"/api/drafts/{draft.id}/approve", json={"editedBody": "hijacked"})
    assert response.status_code == 403
    mock_send.assert_not_called()


def test_coach_cannot_reject_another_clients_draft():
    session = _session(CLIENT_B)
    draft = _draft(session)
    mock_reject = AsyncMock()
    with (
        patch("app.api.routes.drafts.get_draft", new=AsyncMock(return_value=draft)),
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch("app.api.routes.drafts.mark_draft_rejected", new=mock_reject),
    ):
        response = _as(_coach()).post(f"/api/drafts/{draft.id}/reject", json={"reason": "x"})
    assert response.status_code == 403
    mock_reject.assert_not_called()


def test_approve_sends_to_the_sessions_own_client():
    session = _session(CLIENT_A)
    draft = _draft(session)
    client = Client(
        id=CLIENT_A, name="Jane", email="jane@example.com", coach_user_id=uuid4(), tenant_id="tenant_a"
    )
    mock_send = AsyncMock()
    with (
        patch("app.api.routes.drafts.get_draft", new=AsyncMock(return_value=draft)),
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch("app.api.routes.drafts.get_client_by_id", new=AsyncMock(return_value=client)),
        patch("app.api.routes.drafts.send_email", new=mock_send),
        patch("app.api.routes.drafts.mark_draft_sent", new=AsyncMock()),
    ):
        response = _as(_coach()).post(f"/api/drafts/{draft.id}/approve", json={})
    assert response.status_code == 200
    assert mock_send.call_args.kwargs["to"] == "jane@example.com"


# --- Scorecards and sessions ----------------------------------------------------


def test_coach_cannot_read_another_clients_scorecard():
    session = _session(CLIENT_B)
    with patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)):
        response = _as(_coach()).get(f"/api/scorecards/{session.id}")
    assert response.status_code == 403


def test_coach_cannot_read_another_clients_prep():
    session = _session(CLIENT_B)
    with patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)):
        response = _as(_coach()).get(f"/api/sessions/{session.id}/prep")
    assert response.status_code == 403


def test_session_list_is_restricted_and_cannot_filter_to_another_client():
    mock_list = AsyncMock(return_value=[])
    with patch("app.api.routes.sessions.list_sessions", new=mock_list):
        client = _as(_coach())
        assert client.get("/api/sessions").status_code == 200
        assert mock_list.call_args.args[0] == [CLIENT_A]
        assert client.get(f"/api/sessions?client_id={CLIENT_B}").status_code == 403


def test_cached_prep_is_served_without_calling_gemini():
    session = _session(CLIENT_A)
    mock_generate = AsyncMock()
    with (
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch("app.api.routes.sessions.get_coach_briefing", new=AsyncMock(return_value={"keypoints": ["Cached"]})),
        patch("app.api.routes.sessions.load_prior_sessions", new=AsyncMock(return_value=[])),
        patch("app.api.routes.sessions.generate", new=mock_generate),
    ):
        response = _as(_coach()).get(f"/api/sessions/{session.id}/prep")
    assert response.status_code == 200
    assert response.json()["keypoints"] == ["Cached"]
    mock_generate.assert_not_called()


# --- Context Library ----------------------------------------------------------


def test_context_library_list_is_restricted_to_assigned_clients():
    mock_list = AsyncMock(return_value=[])
    with patch("app.api.routes.admin.list_context_library_entries", new=mock_list):
        client = _as(_coach())
        assert client.get("/api/admin/context-library").status_code == 200
        assert mock_list.call_args.args[0] == [CLIENT_A]
        assert client.get(f"/api/admin/context-library?client_id={CLIENT_B}").status_code == 403


def test_coach_cannot_read_history_of_another_clients_entry():
    with patch(
        "app.core.security.get_context_library_group_client_id", new=AsyncMock(return_value=(True, CLIENT_B))
    ):
        response = _as(_coach()).get(f"/api/admin/context-library/{uuid4()}/history")
    assert response.status_code == 403


def test_coach_cannot_create_org_wide_entry():
    mock_create = AsyncMock()
    with patch("app.api.routes.admin.create_context_library_entry_with_embedding", new=mock_create):
        response = _as(_coach()).post("/api/admin/context-library", json={"title": "T", "body": "B"})
    assert response.status_code == 403
    mock_create.assert_not_called()


def test_coach_cannot_write_into_another_clients_library():
    mock_create = AsyncMock()
    with patch("app.api.routes.admin.create_context_library_entry_with_embedding", new=mock_create):
        response = _as(_coach()).post(
            "/api/admin/context-library", json={"clientId": str(CLIENT_B), "title": "T", "body": "B"}
        )
    assert response.status_code == 403
    mock_create.assert_not_called()


def test_coach_cannot_version_an_org_wide_entry():
    mock_post = AsyncMock()
    with (
        patch("app.core.security.get_context_library_group_client_id", new=AsyncMock(return_value=(True, None))),
        patch("app.api.routes.admin.post_context_library_version_with_embedding", new=mock_post),
    ):
        response = _as(_coach()).post(f"/api/admin/context-library/{uuid4()}/versions", json={"title": "T", "body": "B"})
    assert response.status_code == 403
    mock_post.assert_not_called()


def test_admin_can_create_org_wide_entry():
    row = {
        "id": str(uuid4()), "entry_group_id": str(uuid4()), "client_id": None, "title": "ICF", "body": "B",
        "version": 1, "created_at": "2026-09-18T00:00:00Z",
    }
    with patch("app.api.routes.admin.create_context_library_entry_with_embedding", new=AsyncMock(return_value=row)):
        response = _as(_admin()).post("/api/admin/context-library", json={"title": "ICF", "body": "B"})
    assert response.status_code == 200


# --- Client email (the send address) ------------------------------------------


def test_coach_cannot_change_a_clients_email():
    existing = Client(
        id=CLIENT_A, name="Jane", email="jane@example.com", coach_user_id=uuid4(), tenant_id="tenant_a"
    )
    mock_update = AsyncMock()
    with (
        patch("app.api.routes.clients.get_client_by_id", new=AsyncMock(return_value=existing)),
        patch("app.api.routes.clients.update_client", new=mock_update),
    ):
        response = _as(_coach()).put(f"/api/clients/{CLIENT_A}", json={"email": "someone@else.com"})
    assert response.status_code == 403
    mock_update.assert_not_called()


def test_coach_cannot_analyse_another_clients_session():
    session = _session(CLIENT_B)
    mock_run = AsyncMock()
    with (
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch("app.api.routes.sessions.run_post_session_analysis", new=mock_run),
    ):
        response = _as(_coach()).post(f"/api/sessions/{session.id}/analysis")
    assert response.status_code == 403
    mock_run.assert_not_called()


def test_analysis_without_a_transcript_is_409():
    from app.services.post_session import PostSessionError

    session = _session(CLIENT_A)
    with (
        patch("app.core.security.get_session_by_id", new=AsyncMock(return_value=session)),
        patch(
            "app.api.routes.sessions.run_post_session_analysis",
            new=AsyncMock(side_effect=PostSessionError("no_transcript", "No transcript is linked")),
        ),
    ):
        response = _as(_coach()).post(f"/api/sessions/{session.id}/analysis")
    assert response.status_code == 409
    assert response.json()["detail"] == "No transcript is linked"
