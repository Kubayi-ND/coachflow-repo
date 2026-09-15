from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.ai.gemini_client import generate
from app.core.security import assert_client_access, get_current_user
from app.db.repository import (
    get_current_prompt_template,
    get_supabase,
    list_sessions,
    list_unmatched_events,
    row_of,
)
from app.models.session import (
    Session,
    SessionHistoryItem,
    SessionPrep,
    UnmatchedEvent,
    UnmatchedEventResolve,
)
from app.models.user import User
from app.services.context_builder import build_context

router = APIRouter()


@router.get("", response_model=list[Session])
async def get_sessions(
    tenant_id: str | None = None,
    client_id: UUID | None = None,
    user: User = Depends(get_current_user),
) -> list[Session]:
    return await list_sessions(tenant_id=tenant_id, client_id=client_id)


@router.get("/{session_id}/prep", response_model=SessionPrep)
async def get_session_prep(session_id: UUID, user: User = Depends(get_current_user)) -> SessionPrep:
    session_row = row_of(get_supabase().table("sessions").select("*").eq("id", str(session_id)).limit(1).execute())
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = Session(**session_row)
    assert_client_access(user, session.client_id)
    context = await build_context(session.client_id, session.type, exclude_session_id=session.id)
    template = await get_current_prompt_template(session.type, "pre")
    if template is None:
        raise HTTPException(status_code=409, detail="No pre-session prompt configured")

    result = await generate(template["body"].format(**context.as_prompt_vars()), structured=True)
    payload = result.as_json()
    history = [
        SessionHistoryItem(id=row["id"], event_date=row["event_date"], summary=row.get("summary"))
        for row in context.prior_sessions
    ]
    latest_review_session_id = context.prior_sessions[0]["id"] if context.prior_sessions else None
    scorecard_row = (
        row_of(
            get_supabase()
            .table("scorecards")
            .select("structured_critique,citations")
            .eq("session_id", latest_review_session_id)
            .limit(1)
            .execute()
        )
        if latest_review_session_id
        else None
    )
    return SessionPrep(
        session=session,
        keypoints=payload["keypoints"],
        scorecard=scorecard_row.get("structured_critique") if scorecard_row else None,
        citations=scorecard_row.get("citations", []) if scorecard_row else [],
        history=history,
    )


@router.get("/unmatched-events", response_model=list[UnmatchedEvent])
async def get_unmatched_events(
    tenant_id: str | None = None, user: User = Depends(get_current_user)
) -> list[UnmatchedEvent]:
    return await list_unmatched_events(tenant_id=tenant_id)


@router.post("/unmatched-events/{event_id}/resolve", response_model=UnmatchedEvent)
async def resolve_unmatched_event(
    event_id: UUID, body: UnmatchedEventResolve, user: User = Depends(get_current_user)
) -> UnmatchedEvent:
    """One-click "assign session type" action from the Calendar view's
    unmatched-events exception-handling UI (frontend/CLAUDE.md)."""
    from app.db.repository import get_supabase, row_of

    result = (
        get_supabase()
        .table("unmatched_events")
        .update({"resolved_session_type": body.resolved_session_type.value})
        .eq("id", str(event_id))
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return UnmatchedEvent(**row)
