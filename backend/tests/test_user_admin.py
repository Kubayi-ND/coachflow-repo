"""Admin user management + password reset. Covers the repository functions
directly (matching test_draft_generation_flow.py's _FakeSupabase convention)
and, for the first time in this repo, a route-level test through the actual
ASGI app via TestClient + app.dependency_overrides — see backend/CLAUDE.md's
testing notes and the implementation plan for why this pattern is new here.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user, require_admin
from app.models.user import User, UserRole, UserStatus


class _FakeTable:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filtered = rows
        self.updated: dict | None = None

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filtered = [r for r in self._filtered if r.get(key) == value]
        return self

    def neq(self, key, value):
        self._filtered = [r for r in self._filtered if r.get(key) != value]
        return self

    def insert(self, row: dict):
        self._rows.append(row)
        self._filtered = [row]
        return self

    def update(self, values: dict):
        self.updated = values
        for row in self._filtered:
            row.update(values)
        return self

    def execute(self):
        return MagicMock(data=self._filtered)


class _FakeSupabase:
    def __init__(self, users: list[dict]):
        self._users = users

    def table(self, name: str):
        assert name == "users"
        return _FakeTable(self._users)


def _admin_user() -> User:
    return User(id=uuid4(), email="admin@example.com", role=UserRole.ADMIN, status=UserStatus.ACTIVE)


def _make_client() -> TestClient:
    from app.main import app

    return TestClient(app)


# --- Repository-level -------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_excludes_deleted_by_default():
    from app.db import repository

    users = [
        {"id": str(uuid4()), "email": "a@example.com", "role": "admin", "status": "active", "assigned_client_ids": [], "created_at": "2024-01-01T00:00:00Z"},
        {"id": str(uuid4()), "email": "b@example.com", "role": "general", "status": "deleted", "assigned_client_ids": [], "created_at": "2024-01-01T00:00:00Z"},
    ]
    with patch.object(repository, "get_supabase", return_value=_FakeSupabase(users)):
        result = await repository.list_users()

    assert [u.email for u in result] == ["a@example.com"]


@pytest.mark.asyncio
async def test_create_user_record_inserts_active_status():
    from app.db import repository

    with patch.object(repository, "get_supabase", return_value=_FakeSupabase([])):
        user = await repository.create_user_record(uuid4(), "new@example.com", UserRole.GENERAL)

    assert user.status == UserStatus.ACTIVE
    assert user.email == "new@example.com"
    assert user.must_reset_password is True  # default: admin-provisioned accounts force a reset


@pytest.mark.asyncio
async def test_complete_password_reset_clears_flag():
    from app.db import repository

    user_id = uuid4()
    users = [
        {
            "id": str(user_id),
            "email": "coach@example.com",
            "role": "general",
            "status": "active",
            "must_reset_password": True,
            "assigned_client_ids": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    with patch.object(repository, "get_supabase", return_value=_FakeSupabase(users)):
        result = await repository.complete_password_reset(user_id)

    assert result is not None
    assert result.must_reset_password is False


@pytest.mark.asyncio
async def test_complete_password_reset_returns_none_for_missing_user():
    from app.db import repository

    with patch.object(repository, "get_supabase", return_value=_FakeSupabase([])):
        result = await repository.complete_password_reset(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_update_user_status_returns_none_for_missing_user():
    from app.db import repository

    with patch.object(repository, "get_supabase", return_value=_FakeSupabase([])):
        result = await repository.update_user_status(uuid4(), UserStatus.SUSPENDED)

    assert result is None


# --- get_current_user status enforcement ------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_rejects_suspended_user():
    from app.core import security

    suspended = User(id=uuid4(), email="s@example.com", role=UserRole.GENERAL, status=UserStatus.SUSPENDED)
    with (
        patch.object(security, "_get_jwks", new=AsyncMock(return_value={})),
        patch("app.core.security.jwt.decode", return_value={"sub": str(suspended.id)}),
        patch.object(security, "get_user_by_id", new=AsyncMock(return_value=suspended)),
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await security.get_current_user(credentials=MagicMock(credentials="token"))

    assert exc_info.value.status_code == 403


# --- Route-level (TestClient + dependency_overrides) ------------------------


@pytest.fixture
def admin_client():
    from app.main import app

    admin = _admin_user()
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_current_user] = lambda: admin
    yield TestClient(app), admin
    app.dependency_overrides.clear()


def test_create_user_route_happy_path(admin_client):
    client, _admin = admin_client
    new_id = uuid4()

    with (
        patch("app.api.routes.admin.get_user_by_email", new=AsyncMock(return_value=None)),
        patch(
            "app.api.routes.admin.create_user_with_temp_password",
            new=AsyncMock(return_value=(new_id, "a-generated-temp-password")),
        ),
        patch(
            "app.api.routes.admin.create_user_record",
            new=AsyncMock(
                return_value=User(
                    id=new_id,
                    email="new@example.com",
                    role=UserRole.GENERAL,
                    status=UserStatus.ACTIVE,
                    must_reset_password=True,
                )
            ),
        ),
    ):
        response = client.post("/api/admin/users", json={"email": "new@example.com", "role": "general"})

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["mustResetPassword"] is True
    assert body["temporaryPassword"] == "a-generated-temp-password"


def test_create_user_route_rolls_back_auth_account_on_users_insert_failure(admin_client):
    client, _admin = admin_client
    new_id = uuid4()

    with (
        patch("app.api.routes.admin.get_user_by_email", new=AsyncMock(return_value=None)),
        patch(
            "app.api.routes.admin.create_user_with_temp_password",
            new=AsyncMock(return_value=(new_id, "a-generated-temp-password")),
        ),
        patch("app.api.routes.admin.create_user_record", new=AsyncMock(side_effect=RuntimeError("insert failed"))),
        patch("app.api.routes.admin.get_supabase") as mock_get_supabase,
        pytest.raises(RuntimeError),
    ):
        mock_delete_user = mock_get_supabase.return_value.auth.admin.delete_user
        client.post("/api/admin/users", json={"email": "new@example.com", "role": "general"})

    mock_delete_user.assert_called_once_with(str(new_id))


def test_create_user_route_conflict_on_existing_email(admin_client):
    client, admin = admin_client

    with patch("app.api.routes.admin.get_user_by_email", new=AsyncMock(return_value=admin)):
        response = client.post("/api/admin/users", json={"email": admin.email, "role": "general"})

    assert response.status_code == 409


def test_suspend_user_route(admin_client):
    client, _admin = admin_client
    target_id = uuid4()
    suspended = User(id=target_id, email="t@example.com", role=UserRole.GENERAL, status=UserStatus.SUSPENDED)

    with patch("app.api.routes.admin.update_user_status", new=AsyncMock(return_value=suspended)):
        response = client.post(f"/api/admin/users/{target_id}/suspend")

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_suspend_self_is_rejected(admin_client):
    client, admin = admin_client

    response = client.post(f"/api/admin/users/{admin.id}/suspend")

    assert response.status_code == 400


def test_delete_user_route_returns_204(admin_client):
    client, _admin = admin_client
    target_id = uuid4()
    deleted = User(id=target_id, email="t@example.com", role=UserRole.GENERAL, status=UserStatus.DELETED)

    with patch("app.api.routes.admin.update_user_status", new=AsyncMock(return_value=deleted)):
        response = client.delete(f"/api/admin/users/{target_id}")

    assert response.status_code == 204


# --- /api/auth/forgot-password ----------------------------------------------


def test_forgot_password_always_returns_204_even_on_send_failure():
    client = _make_client()

    with patch(
        "app.api.routes.auth.send_password_reset_email",
        new=AsyncMock(side_effect=RuntimeError("supabase down")),
    ):
        response = client.post("/api/auth/forgot-password", json={"email": "anyone@example.com"})

    assert response.status_code == 204


# --- /api/auth/complete-password-reset --------------------------------------


def test_complete_password_reset_route_clears_flag():
    from app.main import app

    coach = User(
        id=uuid4(), email="coach@example.com", role=UserRole.GENERAL, status=UserStatus.ACTIVE, must_reset_password=True
    )
    reset_coach = coach.model_copy(update={"must_reset_password": False})
    app.dependency_overrides[get_current_user] = lambda: coach
    try:
        with patch(
            "app.api.routes.auth.complete_password_reset", new=AsyncMock(return_value=reset_coach)
        ):
            client = TestClient(app)
            response = client.post("/api/auth/complete-password-reset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["mustResetPassword"] is False
