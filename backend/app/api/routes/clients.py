from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import assert_client_access, get_current_user, require_coach_or_admin
from app.db.repository import (
    add_assigned_client,
    create_client,
    delete_client,
    get_client_by_id,
    list_clients_for_user,
    remove_assigned_client,
    update_client,
)
from app.models.client import Client, ClientCreate, ClientUpdate
from app.models.user import User
from app.services.context_library_admin import create_context_library_entry_with_embedding

router = APIRouter()


@router.get("", response_model=list[Client])
async def get_clients(user: User = Depends(get_current_user)) -> list[Client]:
    return await list_clients_for_user(user)


@router.post("", response_model=Client, status_code=status.HTTP_201_CREATED)
async def create_client_route(body: ClientCreate, user: User = Depends(require_coach_or_admin)) -> Client:
    """A client is always self-assigned to the creating coach — see
    app/models/client.py's ClientCreate docstring. assigned_client_ids (the
    array core.security actually gates access on, not clients.coach_user_id)
    must be updated here too or the coach couldn't see/edit what they just
    made."""
    client = await create_client(
        coach_user_id=user.id,
        name=body.name,
        email=body.email,
        tenant_id=body.tenant_id,
        drive_folder_id=body.drive_folder_id,
        session_types=body.session_types,
    )
    await add_assigned_client(user.id, client.id)
    if body.context:
        await create_context_library_entry_with_embedding(client.id, f"{body.name} — Coaching Context", body.context)
    return client


@router.put("/{client_id}", response_model=Client)
async def update_client_route(
    client_id: UUID, body: ClientUpdate, user: User = Depends(require_coach_or_admin)
) -> Client:
    assert_client_access(user, client_id)
    existing = await get_client_by_id(client_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")

    updates = body.model_dump(exclude_unset=True, mode="json")
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    updated = await update_client(client_id, updates)
    assert updated is not None
    return updated


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_route(client_id: UUID, user: User = Depends(require_coach_or_admin)) -> None:
    assert_client_access(user, client_id)
    existing = await get_client_by_id(client_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")

    await delete_client(client_id)
    await remove_assigned_client(existing.coach_user_id, client_id)
