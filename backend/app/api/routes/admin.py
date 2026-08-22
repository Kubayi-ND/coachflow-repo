from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.security import require_admin
from app.db.repository import (
    create_context_library_entry,
    create_prompt_template,
    create_user_record,
    get_context_library_history,
    get_prompt_template_history,
    get_supabase,
    get_user_by_email,
    list_context_library_entries,
    list_prompt_templates,
    list_users,
    post_context_library_version,
    post_prompt_template_version,
    row_of,
    rows_of,
    update_user_status,
)
from app.models.admin import (
    PromptTemplate,
    PromptTemplateCreate,
    PromptTemplateVersion,
    ReminderRule,
    TenantStatus,
)
from app.models.context_library import (
    ContextLibraryEntry,
    ContextLibraryEntryCreate,
    ContextLibraryEntryVersion,
)
from app.models.user import User, UserCreate, UserStatus
from app.services.user_admin import invite_new_user

router = APIRouter()


@router.get("/reminder-rules", response_model=list[ReminderRule])
async def get_reminder_rules(user: User = Depends(require_admin)) -> list[ReminderRule]:
    rows = rows_of(get_supabase().table("reminder_rules").select("*").execute())
    return [ReminderRule(**row) for row in rows]


@router.put("/reminder-rules/{session_type}", response_model=ReminderRule)
async def update_reminder_rule(session_type: str, body: ReminderRule, user: User = Depends(require_admin)) -> ReminderRule:
    result = (
        get_supabase()
        .table("reminder_rules")
        .update({"lead_time_working_days": body.lead_time_working_days, "naming_pattern": body.naming_pattern})
        .eq("session_type", session_type)
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return ReminderRule(**row)


@router.get("/prompt-templates", response_model=list[PromptTemplate])
async def get_prompt_templates(user: User = Depends(require_admin)) -> list[PromptTemplate]:
    rows = await list_prompt_templates()
    return [PromptTemplate(**row) for row in rows]


@router.get("/prompt-templates/{entry_group_id}/history", response_model=list[PromptTemplate])
async def get_prompt_template_history_route(entry_group_id: UUID, user: User = Depends(require_admin)) -> list[PromptTemplate]:
    rows = await get_prompt_template_history(entry_group_id)
    return [PromptTemplate(**row) for row in rows]


@router.post("/prompt-templates", response_model=PromptTemplate)
async def create_prompt_template_route(body: PromptTemplateCreate, user: User = Depends(require_admin)) -> PromptTemplate:
    try:
        row = await create_prompt_template(body.session_type, body.phase, body.title, body.body)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return PromptTemplate(**row)


@router.post("/prompt-templates/{entry_group_id}/versions", response_model=PromptTemplate)
async def post_prompt_template_version_route(
    entry_group_id: UUID, body: PromptTemplateVersion, user: User = Depends(require_admin)
) -> PromptTemplate:
    try:
        row = await post_prompt_template_version(entry_group_id, body.title, body.body)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return PromptTemplate(**row)


@router.get("/context-library", response_model=list[ContextLibraryEntry])
async def get_context_library_entries(
    client_id: UUID | None = None, user: User = Depends(require_admin)
) -> list[ContextLibraryEntry]:
    rows = await list_context_library_entries(client_id)
    return [ContextLibraryEntry(**row) for row in rows]


@router.get("/context-library/{entry_group_id}/history", response_model=list[ContextLibraryEntry])
async def get_context_library_history_route(
    entry_group_id: UUID, user: User = Depends(require_admin)
) -> list[ContextLibraryEntry]:
    rows = await get_context_library_history(entry_group_id)
    return [ContextLibraryEntry(**row) for row in rows]


@router.post("/context-library", response_model=ContextLibraryEntry)
async def create_context_library_entry_route(
    body: ContextLibraryEntryCreate, user: User = Depends(require_admin)
) -> ContextLibraryEntry:
    row = await create_context_library_entry(body.client_id, body.title, body.body)
    return ContextLibraryEntry(**row)


@router.post("/context-library/{entry_group_id}/versions", response_model=ContextLibraryEntry)
async def post_context_library_version_route(
    entry_group_id: UUID, body: ContextLibraryEntryVersion, user: User = Depends(require_admin)
) -> ContextLibraryEntry:
    try:
        row = await post_context_library_version(entry_group_id, body.title, body.body)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ContextLibraryEntry(**row)


@router.get("/tenants", response_model=list[TenantStatus])
async def get_tenants(user: User = Depends(require_admin)) -> list[TenantStatus]:
    rows = rows_of(get_supabase().table("tenants").select("id,workspace_domain,connected").execute())
    return [TenantStatus(**row) for row in rows]


@router.get("/users", response_model=list[User])
async def get_users(user: User = Depends(require_admin)) -> list[User]:
    return await list_users()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_route(body: UserCreate, user: User = Depends(require_admin)) -> User:
    existing = await get_user_by_email(body.email)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")

    settings = get_settings()
    try:
        new_id = await invite_new_user(body.email, f"{settings.app_base_url}/set-password")
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Failed to send invite email") from exc

    return await create_user_record(new_id, body.email, body.role)


@router.post("/users/{user_id}/suspend", response_model=User)
async def suspend_user_route(user_id: UUID, admin: User = Depends(require_admin)) -> User:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot suspend your own account")
    updated = await update_user_status(user_id, UserStatus.SUSPENDED)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return updated


@router.post("/users/{user_id}/reactivate", response_model=User)
async def reactivate_user_route(user_id: UUID, admin: User = Depends(require_admin)) -> User:
    updated = await update_user_status(user_id, UserStatus.ACTIVE)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return updated


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_route(user_id: UUID, admin: User = Depends(require_admin)) -> None:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")
    updated = await update_user_status(user_id, UserStatus.DELETED)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
