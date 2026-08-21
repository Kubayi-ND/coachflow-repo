"""Runs hourly (jobs/scheduler.py), checks sessions whose computed trigger
date is now, and kicks off context assembly + draft generation — this is what
fires phases A, C, D, and E at the right moment (backend/CLAUDE.md phase 7).

If a linked calendar event's time changes after a job was scheduled, the
calendar scanner's upsert (services/calendar_scanner.py) naturally
recomputes trigger_date on its next pass rather than sending a stale prep
package — this job always reads trigger_date fresh off the sessions table.
"""
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.db.repository import get_supabase, rows_of
from app.services.draft_generator import generate_prep_email_draft
from app.session_types_generated import SessionType

logger = logging.getLogger(__name__)


async def run_due_sessions() -> None:
    supabase = get_supabase()
    now = datetime.now(UTC).isoformat()

    due_sessions = rows_of(
        supabase.table("sessions").select("*").eq("status", "upcoming").lte("trigger_date", now).execute()
    )

    for session in due_sessions:
        try:
            await _trigger_session(session)
        except Exception:
            # A failure for one session must not block the rest of the batch —
            # mirrors the per-tenant isolation rule in the credential vault.
            logger.exception("Failed to trigger session %s", session["id"])


async def _trigger_session(session: dict[str, Any]) -> None:
    session_id = UUID(session["id"])
    client_id = UUID(session["client_id"])
    tenant_id = session["tenant_id"]
    session_type = SessionType(session["type"])

    supabase = get_supabase()
    supabase.table("sessions").update({"status": "prep_generating"}).eq("id", str(session_id)).execute()

    await generate_prep_email_draft(session_id, client_id, tenant_id, session_type)

    supabase.table("sessions").update({"status": "ready_for_review"}).eq("id", str(session_id)).execute()
