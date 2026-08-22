"""Thin data-access layer — one function per table per operation, per
backend/CLAUDE.md. This is also where per-client authorization is enforced
for `general` users (via core.security.assert_client_access), so a new route
can't accidentally read/write another coach's client data.

Uses supabase-py against the Supabase Postgres REST interface (the
hackathon-scale option backend/CLAUDE.md calls out; swap for SQLAlchemy +
Alembic here if the team wants migrations instead — nothing above this layer
needs to change).
"""
from functools import lru_cache
from typing import Any, cast
from uuid import UUID

from supabase import Client, create_client

from app.core.config import get_settings
from app.models.client import Client as ClientModel
from app.models.draft import AiDraft, DraftStatus
from app.models.session import Session, UnmatchedEvent
from app.models.user import User, UserRole, UserStatus
from app.session_types_generated import SessionType


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def rows_of(response: Any) -> list[dict[str, Any]]:
    """postgrest-py's `execute()` isn't generically parameterized in this
    codebase, so mypy infers `.data` as a bare JSON union instead of the list
    of row objects the Supabase REST API actually returns. Every call site
    that reads a query result should route through this (or `row_of`) instead
    of touching `.data` directly."""
    return cast(list[dict[str, Any]], response.data)


def row_of(response: Any) -> dict[str, Any] | None:
    data = rows_of(response)
    return data[0] if data else None


async def get_user_by_id(user_id: UUID) -> User | None:
    result = get_supabase().table("users").select("*").eq("id", str(user_id)).limit(1).execute()
    row = row_of(result)
    return User(**row) if row else None


async def get_user_by_email(email: str) -> User | None:
    result = get_supabase().table("users").select("*").eq("email", email).limit(1).execute()
    row = row_of(result)
    return User(**row) if row else None


async def list_users(include_deleted: bool = False) -> list[User]:
    query = get_supabase().table("users").select("*").order("created_at", desc=True)
    if not include_deleted:
        query = query.neq("status", UserStatus.DELETED.value)
    return [User(**row) for row in rows_of(query.execute())]


async def create_user_record(user_id: UUID, email: str, role: UserRole) -> User:
    result = (
        get_supabase()
        .table("users")
        .insert({"id": str(user_id), "email": email, "role": role.value, "status": UserStatus.ACTIVE.value})
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return User(**row)


async def update_user_status(user_id: UUID, new_status: UserStatus) -> User | None:
    result = get_supabase().table("users").update({"status": new_status.value}).eq("id", str(user_id)).execute()
    row = row_of(result)
    return User(**row) if row else None


async def list_clients_for_user(user: User) -> list[ClientModel]:
    query = get_supabase().table("clients").select("*")
    if user.role != "admin":
        query = query.in_("id", [str(cid) for cid in user.assigned_client_ids])
    return [ClientModel(**row) for row in rows_of(query.execute())]


async def list_sessions(tenant_id: str | None = None, client_id: UUID | None = None) -> list[Session]:
    query = get_supabase().table("sessions").select("*")
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if client_id:
        query = query.eq("client_id", str(client_id))
    return [Session(**row) for row in rows_of(query.execute())]


async def list_unmatched_events(tenant_id: str | None = None) -> list[UnmatchedEvent]:
    query = get_supabase().table("unmatched_events").select("*").is_("resolved_session_type", "null")
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    return [UnmatchedEvent(**row) for row in rows_of(query.execute())]


async def list_drafts(status: DraftStatus | None = None) -> list[AiDraft]:
    query = get_supabase().table("ai_drafts").select("*")
    if status:
        query = query.eq("status", status.value)
    return [AiDraft(**row) for row in rows_of(query.execute())]


async def get_draft(draft_id: UUID) -> AiDraft | None:
    result = get_supabase().table("ai_drafts").select("*").eq("id", str(draft_id)).limit(1).execute()
    row = row_of(result)
    return AiDraft(**row) if row else None


async def mark_draft_sent(draft_id: UUID, body: str) -> None:
    get_supabase().table("ai_drafts").update(
        {"status": DraftStatus.SENT.value, "body": body, "sent_at": "now()"}
    ).eq("id", str(draft_id)).execute()


async def mark_draft_rejected(draft_id: UUID, reason: str) -> None:
    get_supabase().table("ai_drafts").update(
        {"status": DraftStatus.REJECTED.value, "rejection_reason": reason}
    ).eq("id", str(draft_id)).execute()


# --- Context Library --------------------------------------------------------
# Append-only: edits post a new version rather than overwrite (per
# backend/CLAUDE.md's Context Library admin ownership + the append-only
# history the product requires). Reads go through the `_current` view so
# generation and the admin list never see stale versions.


async def list_context_library_entries(client_id: UUID | None = None) -> list[dict[str, Any]]:
    query = get_supabase().table("context_library_current").select("*")
    if client_id:
        query = query.or_(f"client_id.eq.{client_id},client_id.is.null")
    return rows_of(query.execute())


async def get_context_library_history(entry_group_id: UUID) -> list[dict[str, Any]]:
    query = (
        get_supabase()
        .table("context_library")
        .select("*")
        .eq("entry_group_id", str(entry_group_id))
        .order("version", desc=True)
    )
    return rows_of(query.execute())


async def create_context_library_entry(client_id: UUID | None, title: str, body: str) -> dict[str, Any]:
    result = (
        get_supabase()
        .table("context_library")
        .insert({"client_id": str(client_id) if client_id else None, "title": title, "body": body, "version": 1})
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row


async def post_context_library_version(entry_group_id: UUID, title: str, body: str) -> dict[str, Any]:
    current = row_of(
        get_supabase()
        .table("context_library_current")
        .select("*")
        .eq("entry_group_id", str(entry_group_id))
        .limit(1)
        .execute()
    )
    if current is None:
        raise LookupError(f"No Context Library entry group {entry_group_id}")
    result = (
        get_supabase()
        .table("context_library")
        .insert(
            {
                "entry_group_id": str(entry_group_id),
                "client_id": current["client_id"],
                "title": title,
                "body": body,
                "version": current["version"] + 1,
            }
        )
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row


# --- Prompt templates --------------------------------------------------------
# Same append-only shape as Context Library. get_current_prompt_template is
# the read path draft_generator.py and scorecard_generator.py call at
# generation time — this table (via its `_current` view) is the live source
# of prompt text, not just an editor's backing store.


async def list_prompt_templates() -> list[dict[str, Any]]:
    return rows_of(get_supabase().table("prompt_templates_current").select("*").execute())


async def get_prompt_template_history(entry_group_id: UUID) -> list[dict[str, Any]]:
    query = (
        get_supabase()
        .table("prompt_templates")
        .select("*")
        .eq("entry_group_id", str(entry_group_id))
        .order("version", desc=True)
    )
    return rows_of(query.execute())


async def get_current_prompt_template(session_type: SessionType, phase: str) -> dict[str, Any] | None:
    result = (
        get_supabase()
        .table("prompt_templates_current")
        .select("*")
        .eq("session_type", session_type.value)
        .eq("phase", phase)
        .limit(1)
        .execute()
    )
    return row_of(result)


async def create_prompt_template(session_type: SessionType, phase: str, title: str, body: str) -> dict[str, Any]:
    existing = row_of(
        get_supabase()
        .table("prompt_templates_current")
        .select("id")
        .eq("session_type", session_type.value)
        .eq("phase", phase)
        .limit(1)
        .execute()
    )
    if existing is not None:
        raise ValueError(f"A prompt template already exists for {session_type.value}/{phase} — post a new version instead")
    result = (
        get_supabase()
        .table("prompt_templates")
        .insert({"session_type": session_type.value, "phase": phase, "title": title, "body": body, "version": 1})
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row


async def post_prompt_template_version(entry_group_id: UUID, title: str, body: str) -> dict[str, Any]:
    current = row_of(
        get_supabase()
        .table("prompt_templates_current")
        .select("*")
        .eq("entry_group_id", str(entry_group_id))
        .limit(1)
        .execute()
    )
    if current is None:
        raise LookupError(f"No prompt template group {entry_group_id}")
    result = (
        get_supabase()
        .table("prompt_templates")
        .insert(
            {
                "entry_group_id": str(entry_group_id),
                "session_type": current["session_type"],
                "phase": current["phase"],
                "title": title,
                "body": body,
                "version": current["version"] + 1,
            }
        )
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row
