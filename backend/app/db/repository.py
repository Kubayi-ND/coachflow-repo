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
from app.models.user import User


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
