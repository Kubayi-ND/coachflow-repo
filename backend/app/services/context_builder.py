"""Assembles client profile + Context Library slice + prior sessions of the
same type only — a 1-on-1 draft must never pull strategic-council history and
vice versa (backend/CLAUDE.md phase 4).
"""
from typing import Any
from uuid import UUID

from app.db.repository import get_supabase, rows_of
from app.session_types_generated import SessionType


class AssembledContext:
    def __init__(
        self,
        client_profile: dict[str, Any],
        context_library: list[dict[str, Any]],
        prior_sessions: list[dict[str, Any]],
    ):
        self.client_profile = client_profile
        self.context_library = context_library
        self.prior_sessions = prior_sessions

    def as_prompt_vars(self) -> dict[str, str]:
        return {
            "client_profile": _format_client_profile(self.client_profile),
            "context_library": _format_context_library(self.context_library),
            "prior_sessions": _format_prior_sessions(self.prior_sessions),
        }


async def build_context(client_id: UUID, session_type: SessionType, exclude_session_id: UUID | None = None) -> AssembledContext:
    supabase = get_supabase()

    client_row = rows_of(supabase.table("clients").select("*").eq("id", str(client_id)).limit(1).execute())
    client_profile = client_row[0] if client_row else {}

    context_rows = rows_of(
        supabase.table("context_library_current")
        .select("*")
        .or_(f"client_id.eq.{client_id},client_id.is.null")
        .execute()
    )

    prior_query = (
        supabase.table("sessions")
        .select("*")
        .eq("client_id", str(client_id))
        .eq("type", session_type.value)
        .eq("status", "sent")
        .order("event_date", desc=True)
        .limit(5)
    )
    prior_sessions = [row for row in rows_of(prior_query.execute()) if row["id"] != str(exclude_session_id)]

    return AssembledContext(client_profile, context_rows, prior_sessions)


def _format_client_profile(profile: dict[str, Any]) -> str:
    if not profile:
        return "(no client profile on file)"
    return f"Name: {profile.get('name', 'unknown')}"


def _format_context_library(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "(no Context Library entries matched)"
    return "\n\n".join(f"### {entry['title']} (v{entry['version']}, id={entry['id']})\n{entry['body']}" for entry in entries)


def _format_prior_sessions(sessions: list[dict[str, Any]]) -> str:
    if not sessions:
        return "(no prior sessions of this type)"
    return "\n".join(f"- {session['event_date']}: session id {session['id']}" for session in sessions)
