from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import assert_session_access, get_current_user
from app.db.repository import get_supabase, row_of
from app.models.scorecard import Scorecard
from app.models.user import User

router = APIRouter()


@router.get("/{session_id}", response_model=Scorecard)
async def get_scorecard(session_id: UUID, user: User = Depends(get_current_user)) -> Scorecard:
    await assert_session_access(user, session_id)
    row = row_of(
        get_supabase().table("scorecards").select("*").eq("session_id", str(session_id)).limit(1).execute()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scorecard not found")
    return Scorecard(**row)
