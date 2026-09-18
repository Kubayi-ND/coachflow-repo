"""Assembles client profile + Context Library slice + prior sessions of the
same type only — a 1-on-1 draft must never pull strategic-council history and
vice versa (backend/CLAUDE.md phase 4).

Everything a prompt may contain is decided by resolve_retrieval_scope — the
single retrieval-scope function CLAUDE.md requires. Today a scope is one
client plus org-wide reference material; company/team engagements and
explicit shares plug in here later, not in the callers. Every row fetched is
re-checked against the scope before it can reach a prompt, so a bug in a
query (or the RPC) fails closed instead of leaking another client's data.

Context Library retrieval: org-wide ICF/GROW entries are always included
unranked (foundational material every session should ground against);
client-specific entries are ranked by embedding similarity against a query
built from the transcript (post-session) or a synthetic session-type +
client-profile query (pre-session, no transcript exists yet).
"""
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.ai.embeddings import embed_query_text
from app.db.repository import get_supabase, match_context_library, rows_of
from app.session_types_generated import SESSION_TYPES, SessionType

_CLIENT_SPECIFIC_MATCH_COUNT = 6
_TRANSCRIPT_QUERY_HEAD_CHARS = 4000
_TRANSCRIPT_QUERY_TAIL_CHARS = 4000
_TRANSCRIPT_QUERY_CAP_CHARS = _TRANSCRIPT_QUERY_HEAD_CHARS + _TRANSCRIPT_QUERY_TAIL_CHARS


@dataclass(frozen=True)
class RetrievalScope:
    client_id: UUID

    def allows_library_row(self, row: dict[str, Any]) -> bool:
        owner = row.get("client_id")
        return owner is None or str(owner) == str(self.client_id)

    def allows_session_row(self, row: dict[str, Any]) -> bool:
        return str(row.get("client_id")) == str(self.client_id)


def resolve_retrieval_scope(client_id: UUID) -> RetrievalScope:
    return RetrievalScope(client_id=client_id)


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


async def build_context(
    client_id: UUID,
    session_type: SessionType,
    exclude_session_id: UUID | None = None,
    transcript_text: str | None = None,
) -> AssembledContext:
    supabase = get_supabase()
    scope = resolve_retrieval_scope(client_id)

    client_row = rows_of(supabase.table("clients").select("*").eq("id", str(scope.client_id)).limit(1).execute())
    client_profile = client_row[0] if client_row else {}

    query_text = _build_query_text(transcript_text, client_profile, session_type)
    query_embedding = await embed_query_text(query_text)

    org_wide_rows = rows_of(
        supabase.table("context_library_current").select("*").is_("client_id", "null").execute()
    )
    ranked_client_rows = await match_context_library(
        query_embedding, scope.client_id, match_count=_CLIENT_SPECIFIC_MATCH_COUNT
    )
    context_rows = [row for row in _merge_context_rows(org_wide_rows, ranked_client_rows) if scope.allows_library_row(row)]

    prior_sessions = await load_prior_sessions(scope, session_type, exclude_session_id)
    return AssembledContext(client_profile, context_rows, prior_sessions)


async def load_prior_sessions(
    scope: RetrievalScope, session_type: SessionType, exclude_session_id: UUID | None = None
) -> list[dict[str, Any]]:
    """Prior sent sessions of the same type inside the scope, newest first,
    each with its sent summary attached. No AI call — the prep route reuses
    this when serving a cached briefing."""
    supabase = get_supabase()
    prior_query = (
        supabase.table("sessions")
        .select("*")
        .eq("client_id", str(scope.client_id))
        .eq("type", session_type.value)
        .eq("status", "sent")
        .order("event_date", desc=True)
        .limit(5)
    )
    prior_sessions = [
        row
        for row in rows_of(prior_query.execute())
        if row["id"] != str(exclude_session_id) and scope.allows_session_row(row)
    ]
    _attach_prior_session_summaries(supabase, prior_sessions)
    return prior_sessions


def _build_query_text(transcript_text: str | None, client_profile: dict[str, Any], session_type: SessionType) -> str:
    if transcript_text:
        if len(transcript_text) > _TRANSCRIPT_QUERY_CAP_CHARS:
            return (
                transcript_text[:_TRANSCRIPT_QUERY_HEAD_CHARS]
                + " ... "
                + transcript_text[-_TRANSCRIPT_QUERY_TAIL_CHARS:]
            )
        return transcript_text

    label = SESSION_TYPES[session_type].label
    name = client_profile.get("name", "this client")
    return (
        f"Upcoming {label} coaching session for {name}. "
        "Relevant ICF coaching competencies and GROW model guidance for this "
        "client's coaching profile and goals."
    )


def _merge_context_rows(org_wide_rows: list[dict[str, Any]], ranked_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids = {row["id"] for row in org_wide_rows}
    merged = list(org_wide_rows)
    merged.extend(row for row in ranked_rows if row["id"] not in seen_ids)
    return merged


def _attach_prior_session_summaries(supabase: Any, prior_sessions: list[dict[str, Any]]) -> None:
    if not prior_sessions:
        return
    session_ids = [session["id"] for session in prior_sessions]
    summary_rows = rows_of(
        supabase.table("ai_drafts")
        .select("session_id,body")
        .in_("session_id", session_ids)
        .eq("draft_type", "summary")
        .eq("status", "sent")
        .execute()
    )
    summary_by_session_id = {row["session_id"]: row["body"] for row in summary_rows}
    for session in prior_sessions:
        session["summary"] = summary_by_session_id.get(session["id"])


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
    lines = []
    for session in sessions:
        summary = session.get("summary")
        if summary:
            lines.append(f"### {session['event_date']} (session id {session['id']})\n{summary}")
        else:
            lines.append(f"- {session['event_date']}: session id {session['id']} (no sent summary on file)")
    return "\n\n".join(lines)
