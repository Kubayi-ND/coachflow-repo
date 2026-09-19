from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.ai.gemini_client import generate
from app.ai.prompt_render import render_prompt
from app.core.security import (
    accessible_client_ids,
    assert_client_access,
    assert_session_access,
    get_current_user,
)
from app.db.repository import (
    get_coach_briefing,
    get_current_prompt_template,
    get_supabase,
    list_sessions,
    list_unmatched_events,
    row_of,
    save_coach_briefing,
)
from app.models.scorecard import Scorecard
from app.models.session import (
    Session,
    SessionHistoryItem,
    SessionPrep,
    UnmatchedEvent,
    UnmatchedEventResolve,
)
from app.models.user import User
from app.services.context_builder import build_context, load_prior_sessions, resolve_retrieval_scope
from app.services.post_session import PostSessionError, run_post_session_analysis

router = APIRouter()


@router.get("", response_model=list[Session])
async def get_sessions(
    tenant_id: str | None = None,
    client_id: UUID | None = None,
    user: User = Depends(get_current_user),
) -> list[Session]:
    if client_id is not None:
        assert_client_access(user, client_id)
    return await list_sessions(accessible_client_ids(user), tenant_id=tenant_id, client_id=client_id)


@router.get("/{session_id}/prep", response_model=SessionPrep)
async def get_session_prep(
    session_id: UUID, refresh: bool = False, user: User = Depends(get_current_user)
) -> SessionPrep:
    """Serves the stored coach briefing (coach_briefings, D-07). Gemini is only
    called when none exists yet or the coach explicitly asks to refresh —
    viewing a session must not re-send its client's data every page load."""
    session = await assert_session_access(user, session_id)
    scope = resolve_retrieval_scope(session.client_id)

    cached = None if refresh else await get_coach_briefing(session.id)
    if cached is not None:
        keypoints = cached["keypoints"]
        prior_sessions = await load_prior_sessions(scope, session.type, exclude_session_id=session.id)
    else:
        context = await build_context(session.client_id, session.type, exclude_session_id=session.id)
        template = await get_current_prompt_template(session.type, "pre")
        if template is None:
            raise HTTPException(status_code=409, detail="No pre-session prompt configured")
        result = await generate(render_prompt(template["body"], context.as_prompt_vars()), structured=True)
        keypoints = result.as_json()["keypoints"]
        await save_coach_briefing(session.id, keypoints)
        prior_sessions = context.prior_sessions

    history = [
        SessionHistoryItem(id=row["id"], event_date=row["event_date"], summary=row.get("summary"))
        for row in prior_sessions
    ]
    latest_review_session_id = prior_sessions[0]["id"] if prior_sessions else None
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
        keypoints=keypoints,
        scorecard=scorecard_row.get("structured_critique") if scorecard_row else None,
        citations=scorecard_row.get("citations", []) if scorecard_row else [],
        history=history,
    )


_ANALYSIS_ERROR_STATUS = {
    "no_transcript": 409,
    "transcript_unusable": 409,
    "no_template": 409,
    "invalid_output": 502,
}


@router.post("/{session_id}/analysis", response_model=Scorecard)
async def run_session_analysis(
    session_id: UUID, refresh: bool = False, user: User = Depends(get_current_user)
) -> Scorecard:
    """Coach-triggered ICF critique of a held session (services/post_session.py).
    Returns the stored critique; `refresh=true` regenerates it. Also creates
    the client summary as a pending Approvals draft the first time."""
    await assert_session_access(user, session_id)
    try:
        await run_post_session_analysis(session_id, force=refresh)
    except PostSessionError as exc:
        raise HTTPException(status_code=_ANALYSIS_ERROR_STATUS[exc.reason], detail=str(exc)) from exc
    row = row_of(
        get_supabase()
        .table("scorecards")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    assert row is not None
    return Scorecard(**row)


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
