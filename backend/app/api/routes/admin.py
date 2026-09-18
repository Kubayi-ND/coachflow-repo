import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    accessible_client_ids,
    assert_client_access,
    assert_context_library_group_access,
    assert_context_library_write_access,
    require_admin,
    require_coach_or_admin,
)
from app.db.repository import (
    create_prompt_template,
    create_user_record,
    get_context_library_history,
    get_prompt_template_history,
    get_supabase,
    get_user_by_email,
    list_context_library_entries,
    list_prompt_templates,
    list_reminder_rules_for_user,
    list_users,
    post_prompt_template_version,
    rows_of,
    update_user_status,
    upsert_reminder_rule_for_user,
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
from app.models.user import User, UserCreate, UserCreateResult, UserStatus
from app.services.context_library_admin import (
    create_context_library_entry_with_embedding,
    post_context_library_version_with_embedding,
)
from app.services.user_admin import create_user_with_temp_password

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/reminder-rules", response_model=list[ReminderRule])
async def get_reminder_rules(user: User = Depends(require_coach_or_admin)) -> list[ReminderRule]:
    rows = await list_reminder_rules_for_user(user.id)
    return [ReminderRule(**row) for row in rows]


@router.put("/reminder-rules/{session_type}", response_model=ReminderRule)
async def update_reminder_rule(session_type: str, body: ReminderRule, user: User = Depends(require_coach_or_admin)) -> ReminderRule:
    row = await upsert_reminder_rule_for_user(
        user.id, body.session_type, body.lead_time_working_days, body.naming_pattern
    )
    return ReminderRule(**row)


@router.get("/prompt-templates", response_model=list[PromptTemplate])
async def get_prompt_templates(user: User = Depends(require_coach_or_admin)) -> list[PromptTemplate]:
    rows = await list_prompt_templates()
    return [PromptTemplate(**row) for row in rows]


@router.get("/prompt-templates/{entry_group_id}/history", response_model=list[PromptTemplate])
async def get_prompt_template_history_route(
    entry_group_id: UUID, user: User = Depends(require_coach_or_admin)
) -> list[PromptTemplate]:
    rows = await get_prompt_template_history(entry_group_id)
    return [PromptTemplate(**row) for row in rows]


@router.post("/prompt-templates", response_model=PromptTemplate)
async def create_prompt_template_route(
    body: PromptTemplateCreate, user: User = Depends(require_coach_or_admin)
) -> PromptTemplate:
    try:
        row = await create_prompt_template(body.session_type, body.phase, body.title, body.body)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return PromptTemplate(**row)


@router.post("/prompt-templates/{entry_group_id}/versions", response_model=PromptTemplate)
async def post_prompt_template_version_route(
    entry_group_id: UUID, body: PromptTemplateVersion, user: User = Depends(require_coach_or_admin)
) -> PromptTemplate:
    try:
        row = await post_prompt_template_version(entry_group_id, body.title, body.body)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return PromptTemplate(**row)


@router.get("/context-library", response_model=list[ContextLibraryEntry])
async def get_context_library_entries(
    client_id: UUID | None = None, user: User = Depends(require_coach_or_admin)
) -> list[ContextLibraryEntry]:
    if client_id is not None:
        assert_client_access(user, client_id)
    rows = await list_context_library_entries(accessible_client_ids(user), client_id)
    return [ContextLibraryEntry(**row) for row in rows]


@router.get("/context-library/{entry_group_id}/history", response_model=list[ContextLibraryEntry])
async def get_context_library_history_route(
    entry_group_id: UUID, user: User = Depends(require_coach_or_admin)
) -> list[ContextLibraryEntry]:
    await assert_context_library_group_access(user, entry_group_id)
    rows = await get_context_library_history(entry_group_id)
    return [ContextLibraryEntry(**row) for row in rows]


@router.post("/context-library", response_model=ContextLibraryEntry)
async def create_context_library_entry_route(
    body: ContextLibraryEntryCreate, user: User = Depends(require_coach_or_admin)
) -> ContextLibraryEntry:
    assert_context_library_write_access(user, body.client_id)
    row = await create_context_library_entry_with_embedding(body.client_id, body.title, body.body)
    return ContextLibraryEntry(**row)


@router.post("/context-library/{entry_group_id}/versions", response_model=ContextLibraryEntry)
async def post_context_library_version_route(
    entry_group_id: UUID, body: ContextLibraryEntryVersion, user: User = Depends(require_coach_or_admin)
) -> ContextLibraryEntry:
    client_id = await assert_context_library_group_access(user, entry_group_id)
    assert_context_library_write_access(user, client_id)
    try:
        row = await post_context_library_version_with_embedding(entry_group_id, body.title, body.body)
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


@router.post("/users", response_model=UserCreateResult, status_code=status.HTTP_201_CREATED)
async def create_user_route(body: UserCreate, user: User = Depends(require_admin)) -> UserCreateResult:
    existing = await get_user_by_email(body.email)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")

    try:
        new_id, temp_password = await create_user_with_temp_password(body.email)
    except Exception as exc:
        logger.exception("Failed to create Supabase Auth user for %s", body.email)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Failed to create user account") from exc

    try:
        new_user = await create_user_record(new_id, body.email, body.role, must_reset_password=True)
    except Exception:
        logger.exception("Failed to create users row for %s — rolling back Auth account", body.email)
        get_supabase().auth.admin.delete_user(str(new_id))
        raise

    return UserCreateResult(user=new_user, temporary_password=temp_password)


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
