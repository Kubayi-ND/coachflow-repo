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
from app.models.imports import ImportItemStatus, ImportJobStatus, ImportSource
from app.models.session import Session, UnmatchedEvent
from app.models.user import User, UserRole, UserStatus
from app.session_types_generated import SESSION_TYPES, SessionType


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


async def create_user_record(
    user_id: UUID, email: str, role: UserRole, must_reset_password: bool = True
) -> User:
    result = (
        get_supabase()
        .table("users")
        .insert(
            {
                "id": str(user_id),
                "email": email,
                "role": role.value,
                "status": UserStatus.ACTIVE.value,
                "must_reset_password": must_reset_password,
            }
        )
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return User(**row)


async def update_user_status(user_id: UUID, new_status: UserStatus) -> User | None:
    result = get_supabase().table("users").update({"status": new_status.value}).eq("id", str(user_id)).execute()
    row = row_of(result)
    return User(**row) if row else None


async def complete_password_reset(user_id: UUID) -> User | None:
    result = (
        get_supabase()
        .table("users")
        .update({"must_reset_password": False})
        .eq("id", str(user_id))
        .execute()
    )
    row = row_of(result)
    return User(**row) if row else None


async def list_clients_for_user(user: User) -> list[ClientModel]:
    query = get_supabase().table("clients").select("*")
    if user.role != "admin":
        query = query.in_("id", [str(cid) for cid in user.assigned_client_ids])
    return [ClientModel(**row) for row in rows_of(query.execute())]


async def list_clients_for_tenant(tenant_id: str) -> list[ClientModel]:
    """All clients for a tenant, unfiltered by coach assignment — used by the
    Drive backfill (services/drive_backfill.py) to match subfolder names
    against every client in scope, not just the requesting user's assigned
    ones (the backfill runs as an admin-triggered background task, not on
    behalf of a single coach)."""
    query = get_supabase().table("clients").select("*").eq("tenant_id", tenant_id)
    return [ClientModel(**row) for row in rows_of(query.execute())]


async def get_client_by_id(client_id: UUID) -> ClientModel | None:
    result = get_supabase().table("clients").select("*").eq("id", str(client_id)).limit(1).execute()
    row = row_of(result)
    return ClientModel(**row) if row else None


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


async def list_reminder_rules_for_user(user_id: UUID) -> list[dict[str, Any]]:
    """Return only the authenticated coach's reminder rules."""
    rows = rows_of(
        get_supabase().table("reminder_rules").select("session_type,lead_time_working_days,naming_pattern")
        .eq("user_id", str(user_id)).execute()
    )
    existing = {row["session_type"] for row in rows}
    rows.extend(
        {
            "session_type": session_type.value,
            "lead_time_working_days": definition.lead_time_working_days,
            "naming_pattern": definition.naming_pattern,
        }
        for session_type, definition in SESSION_TYPES.items()
        if session_type.value not in existing
    )
    return rows


async def upsert_reminder_rule_for_user(
    user_id: UUID, session_type: SessionType, lead_time_working_days: int, naming_pattern: str
) -> dict[str, Any]:
    result = get_supabase().table("reminder_rules").upsert(
        {
            "user_id": str(user_id),
            "session_type": session_type.value,
            "lead_time_working_days": lead_time_working_days,
            "naming_pattern": naming_pattern,
        },
        on_conflict="user_id,session_type",
    ).execute()
    row = row_of(result)
    assert row is not None
    return row


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


async def create_context_library_entry(
    client_id: UUID | None, title: str, body: str, embedding: list[float] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_id": str(client_id) if client_id else None,
        "title": title,
        "body": body,
        "version": 1,
    }
    if embedding is not None:
        payload["embedding"] = embedding
    result = get_supabase().table("context_library").insert(payload).execute()
    row = row_of(result)
    assert row is not None
    return row


async def post_context_library_version(
    entry_group_id: UUID, title: str, body: str, embedding: list[float] | None = None
) -> dict[str, Any]:
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
    payload: dict[str, Any] = {
        "entry_group_id": str(entry_group_id),
        "client_id": current["client_id"],
        "title": title,
        "body": body,
        "version": current["version"] + 1,
    }
    if embedding is not None:
        payload["embedding"] = embedding
    result = get_supabase().table("context_library").insert(payload).execute()
    row = row_of(result)
    assert row is not None
    return row


async def match_context_library(query_embedding: list[float], client_id: UUID, match_count: int = 6) -> list[dict[str, Any]]:
    """Ranked, client-specific Context Library retrieval — see the
    match_context_library RPC in db/schema.sql. Org-wide entries are fetched
    separately (unranked) by context_builder.py, not through this function."""
    result = (
        get_supabase()
        .rpc(
            "match_context_library",
            {"query_embedding": query_embedding, "filter_client_id": str(client_id), "match_count": match_count},
        )
        .execute()
    )
    return rows_of(result)


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


# --- Drive backfill (one-time import) ---------------------------------------
# Backs services/drive_backfill.py — tracks each import run and the per-file
# outcome so an admin can watch progress and resolve a file whose per-client
# subfolder didn't match a client, without a new ongoing ingestion pipeline.


async def create_import_job(tenant_id: str, source: ImportSource) -> dict[str, Any]:
    result = (
        get_supabase()
        .table("import_jobs")
        .insert({"tenant_id": tenant_id, "source": source.value, "status": ImportJobStatus.RUNNING.value})
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row


async def update_import_job_progress(
    job_id: UUID,
    *,
    items_total: int | None = None,
    items_succeeded: int | None = None,
    items_failed: int | None = None,
    status: ImportJobStatus | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if items_total is not None:
        payload["items_total"] = items_total
    if items_succeeded is not None:
        payload["items_succeeded"] = items_succeeded
    if items_failed is not None:
        payload["items_failed"] = items_failed
    if error_message is not None:
        payload["error_message"] = error_message
    if status is not None:
        payload["status"] = status.value
        if status != ImportJobStatus.RUNNING:
            payload["completed_at"] = "now()"
    if payload:
        get_supabase().table("import_jobs").update(payload).eq("id", str(job_id)).execute()


async def list_import_jobs(tenant_id: str | None = None) -> list[dict[str, Any]]:
    query = get_supabase().table("import_jobs").select("*").order("started_at", desc=True)
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    return rows_of(query.execute())


async def get_import_job(job_id: UUID) -> dict[str, Any] | None:
    result = get_supabase().table("import_jobs").select("*").eq("id", str(job_id)).limit(1).execute()
    return row_of(result)


async def get_import_item_by_file(tenant_id: str, source: ImportSource, drive_file_id: str) -> dict[str, Any] | None:
    """Pre-check the Drive backfill uses to skip a file it already imported
    on a prior run of the same source, instead of duplicating the resulting
    context_library/transcripts row."""
    result = (
        get_supabase()
        .table("import_items")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("source", source.value)
        .eq("drive_file_id", drive_file_id)
        .limit(1)
        .execute()
    )
    return row_of(result)


async def record_import_item(
    job_id: UUID,
    tenant_id: str,
    source: ImportSource,
    drive_file_id: str,
    file_name: str,
    mime_type: str,
    status: ImportItemStatus,
    client_id: UUID | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    result = (
        get_supabase()
        .table("import_items")
        .insert(
            {
                "job_id": str(job_id),
                "tenant_id": tenant_id,
                "source": source.value,
                "drive_file_id": drive_file_id,
                "file_name": file_name,
                "mime_type": mime_type,
                "status": status.value,
                "client_id": str(client_id) if client_id else None,
                "error_message": error_message,
            }
        )
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return row


async def list_import_items(job_id: UUID) -> list[dict[str, Any]]:
    query = get_supabase().table("import_items").select("*").eq("job_id", str(job_id)).order("created_at")
    return rows_of(query.execute())


async def get_import_item(item_id: UUID) -> dict[str, Any] | None:
    result = get_supabase().table("import_items").select("*").eq("id", str(item_id)).limit(1).execute()
    return row_of(result)


async def update_import_item(
    item_id: UUID, status: ImportItemStatus, client_id: UUID | None = None, error_message: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status.value, "error_message": error_message}
    if client_id is not None:
        payload["client_id"] = str(client_id)
    result = get_supabase().table("import_items").update(payload).eq("id", str(item_id)).execute()
    row = row_of(result)
    assert row is not None
    return row
