from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.db.repository import list_sessions, list_unmatched_events
from app.models.session import Session, UnmatchedEvent, UnmatchedEventResolve
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[Session])
async def get_sessions(
    tenant_id: str | None = None,
    client_id: UUID | None = None,
    user: User = Depends(get_current_user),
) -> list[Session]:
    return await list_sessions(tenant_id=tenant_id, client_id=client_id)


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
