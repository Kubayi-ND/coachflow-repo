"""Client CRUD: self-service creation/edit/delete for coaches, admin retains
full access. Covers the repository functions directly (matching
test_user_admin.py's _FakeTable/_FakeSupabase convention) and the route layer
through TestClient + app.dependency_overrides.

Coverage focuses on the wrinkle this feature turns on: users.assigned_client_ids
(not clients.coach_user_id) is what core.security actually gates access on, so
create/delete must keep it in sync — see app/api/routes/clients.py.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user, require_coach_or_admin
from app.models.client import Client
from app.models.user import User, UserRole, UserStatus
from app.session_types_generated import SessionType


class _FakeTable:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filtered = rows
        self.updated: dict | None = None
        self.deleted = False

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
        row = {"id": str(uuid4()), **row} if "id" not in row else row
        self._rows.append(row)
        self._filtered = [row]
        return self

    def update(self, values: dict):
        self.updated = values
        for row in self._filtered:
            row.update(values)
        return self

    def delete(self):
        self.deleted = True
        for row in list(self._filtered):
            self._rows.remove(row)
        return self

    def execute(self):
        return MagicMock(data=self._filtered)


class _FakeSupabase:
    """Routes table("clients")/table("users") to independent fake tables so
    add_assigned_client/remove_assigned_client (which read/write "users")
    can be asserted alongside clients-table mutations in the same test."""

    def __init__(self, clients: list[dict] | None = None, users: list[dict] | None = None):
        self._tables = {"clients": _FakeTable(clients or []), "users": _FakeTable(users or [])}

    def table(self, name: str):
        return self._tables[name]


def _coach(assigned_client_ids: list | None = None) -> User:
    return User(
        id=uuid4(),
        email="coach@example.com",
        role=UserRole.GENERAL,
        status=UserStatus.ACTIVE,
        assigned_client_ids=assigned_client_ids or [],
    )


def _admin() -> User:
    return User(id=uuid4(), email="admin@example.com", role=UserRole.ADMIN, status=UserStatus.ACTIVE)


# --- Repository-level --------------------------------------------------------


@pytest.mark.asyncio
async def test_create_client_inserts_coach_user_id_and_session_type_values():
    from app.db import repository

    coach_id = uuid4()
    with patch.object(repository, "get_supabase", return_value=_FakeSupabase()):
        client = await repository.create_client(
            coach_user_id=coach_id,
            name="Jamie Rivera",
            email="jamie@example.com",
            tenant_id="tenant_a",
            drive_folder_id=None,
            session_types=[SessionType.ONE_ON_ONE, SessionType.QUARTERLY_REVIEW],
        )

    assert client.coach_user_id == coach_id
    assert client.session_types == [SessionType.ONE_ON_ONE, SessionType.QUARTERLY_REVIEW]


@pytest.mark.asyncio
async def test_update_client_returns_none_for_missing_client():
    from app.db import repository

    with patch.object(repository, "get_supabase", return_value=_FakeSupabase()):
        result = await repository.update_client(uuid4(), {"name": "New Name"})

    assert result is None


@pytest.mark.asyncio
async def test_delete_client_removes_row():
    from app.db import repository

    client_id = uuid4()
    clients = [{"id": str(client_id), "name": "Old Client", "email": "old@example.com", "coach_user_id": str(uuid4()), "tenant_id": "tenant_a", "drive_folder_id": None, "session_types": []}]
    fake = _FakeSupabase(clients=clients)
    with patch.object(repository, "get_supabase", return_value=fake):
        await repository.delete_client(client_id)
        remaining = await repository.get_client_by_id(client_id)

    assert remaining is None


@pytest.mark.asyncio
async def test_add_assigned_client_appends_without_duplicating():
    from app.db import repository

    user_id = uuid4()
    existing_client_id = uuid4()
    new_client_id = uuid4()
    users = [{"id": str(user_id), "email": "c@example.com", "role": "general", "status": "active", "assigned_client_ids": [str(existing_client_id)]}]
    fake = _FakeSupabase(users=users)

    with patch.object(repository, "get_supabase", return_value=fake):
        await repository.add_assigned_client(user_id, new_client_id)
        await repository.add_assigned_client(user_id, new_client_id)  # idempotent
        updated = await repository.get_user_by_id(user_id)

    assert sorted(str(cid) for cid in updated.assigned_client_ids) == sorted([str(existing_client_id), str(new_client_id)])


@pytest.mark.asyncio
async def test_remove_assigned_client_filters_it_out():
    from app.db import repository

    user_id = uuid4()
    client_id = uuid4()
    users = [{"id": str(user_id), "email": "c@example.com", "role": "general", "status": "active", "assigned_client_ids": [str(client_id)]}]
    fake = _FakeSupabase(users=users)

    with patch.object(repository, "get_supabase", return_value=fake):
        await repository.remove_assigned_client(user_id, client_id)
        updated = await repository.get_user_by_id(user_id)

    assert updated.assigned_client_ids == []


# --- Route-level (TestClient + dependency_overrides) ------------------------


def _client_row(client_id, coach_id, **overrides) -> dict:
    row = {
        "id": str(client_id),
        "name": "Jamie Rivera",
        "email": "jamie@example.com",
        "coach_user_id": str(coach_id),
        "tenant_id": "tenant_a",
        "drive_folder_id": None,
        "session_types": [],
    }
    row.update(overrides)
    return row


def _override_as(user: User):
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_coach_or_admin] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    from app.main import app

    app.dependency_overrides.clear()


def test_create_client_route_self_assigns_coach():
    coach = _coach()
    client = _override_as(coach)
    new_client = Client(**_client_row(uuid4(), coach.id))

    with (
        patch("app.api.routes.clients.create_client", new=AsyncMock(return_value=new_client)),
        patch("app.api.routes.clients.add_assigned_client", new=AsyncMock()) as mock_add,
        patch("app.api.routes.clients.create_context_library_entry_with_embedding", new=AsyncMock()) as mock_ctx,
    ):
        response = client.post(
            "/api/clients",
            json={"name": "Jamie Rivera", "email": "jamie@example.com", "tenantId": "tenant_a", "sessionTypes": []},
        )

    assert response.status_code == 201
    mock_add.assert_called_once_with(coach.id, new_client.id)
    mock_ctx.assert_not_called()


def test_create_client_route_seeds_context_library_when_context_provided():
    coach = _coach()
    client = _override_as(coach)
    new_client_id = uuid4()
    new_client = Client(**_client_row(new_client_id, coach.id))

    with (
        patch("app.api.routes.clients.create_client", new=AsyncMock(return_value=new_client)),
        patch("app.api.routes.clients.add_assigned_client", new=AsyncMock()),
        patch("app.api.routes.clients.create_context_library_entry_with_embedding", new=AsyncMock()) as mock_ctx,
    ):
        response = client.post(
            "/api/clients",
            json={
                "name": "Jamie Rivera",
                "email": "jamie@example.com",
                "tenantId": "tenant_a",
                "sessionTypes": [],
                "context": "Prefers direct feedback, working on delegation.",
            },
        )

    assert response.status_code == 201
    mock_ctx.assert_called_once_with(
        new_client_id, "Jamie Rivera — Coaching Context", "Prefers direct feedback, working on delegation."
    )


def test_update_client_route_rejects_unassigned_coach():
    coach = _coach(assigned_client_ids=[])
    client = _override_as(coach)
    target_id = uuid4()

    response = client.put(f"/api/clients/{target_id}", json={"name": "New Name"})

    assert response.status_code == 403


def test_update_client_route_allows_assigned_coach():
    target_id = uuid4()
    coach = _coach(assigned_client_ids=[target_id])
    client = _override_as(coach)
    existing = Client(**_client_row(target_id, coach.id))
    updated = Client(**_client_row(target_id, coach.id, name="New Name"))

    with (
        patch("app.api.routes.clients.get_client_by_id", new=AsyncMock(return_value=existing)),
        patch("app.api.routes.clients.update_client", new=AsyncMock(return_value=updated)),
    ):
        response = client.put(f"/api/clients/{target_id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_update_client_route_404_for_missing_client():
    target_id = uuid4()
    coach = _coach(assigned_client_ids=[target_id])
    client = _override_as(coach)

    with patch("app.api.routes.clients.get_client_by_id", new=AsyncMock(return_value=None)):
        response = client.put(f"/api/clients/{target_id}", json={"name": "New Name"})

    assert response.status_code == 404


def test_delete_client_route_removes_assignment_from_owning_coach():
    admin = _admin()
    client = _override_as(admin)
    target_id = uuid4()
    owning_coach_id = uuid4()
    existing = Client(**_client_row(target_id, owning_coach_id))

    with (
        patch("app.api.routes.clients.get_client_by_id", new=AsyncMock(return_value=existing)),
        patch("app.api.routes.clients.delete_client", new=AsyncMock()) as mock_delete,
        patch("app.api.routes.clients.remove_assigned_client", new=AsyncMock()) as mock_remove,
    ):
        response = client.delete(f"/api/clients/{target_id}")

    assert response.status_code == 204
    mock_delete.assert_called_once_with(target_id)
    mock_remove.assert_called_once_with(owning_coach_id, target_id)


def test_delete_client_route_rejects_unassigned_coach():
    coach = _coach(assigned_client_ids=[])
    client = _override_as(coach)
    target_id = uuid4()

    response = client.delete(f"/api/clients/{target_id}")

    assert response.status_code == 403
