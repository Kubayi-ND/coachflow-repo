from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import accessible_client_ids, assert_session_access, get_current_user
from app.db.repository import (
    get_client_by_id,
    get_draft,
    list_drafts,
    mark_draft_rejected,
    mark_draft_sent,
)
from app.integrations.google.gmail import send_email
from app.models.draft import AiDraft, DraftApprove, DraftReject, DraftStatus
from app.models.session import Session
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[AiDraft])
async def get_drafts(status_filter: DraftStatus | None = None, user: User = Depends(get_current_user)) -> list[AiDraft]:
    return await list_drafts(accessible_client_ids(user), status=status_filter)


@router.post("/{draft_id}/approve", response_model=AiDraft)
async def approve_draft(draft_id: UUID, body: DraftApprove, user: User = Depends(get_current_user)) -> AiDraft:
    """The only code path allowed to call Gmail. Re-reads the draft's
    tenant_id and sends from that tenant's identity, per backend/CLAUDE.md
    phase 6 — never trust a tenant id passed in from the client."""
    draft, session = await _get_accessible_draft(draft_id, user)
    if draft.status != DraftStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft already actioned")

    final_body = body.edited_body if body.edited_body is not None else draft.body

    # The recipient is always the session's own client, re-read here — never
    # an address passed in from the request.
    client = await get_client_by_id(session.client_id)
    if client is None or not client.email:
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft's client has no email address")
    recipient = client.email

    await send_email(draft.tenant_id, to=recipient, subject=f"CoachFlow: {draft.draft_type.value}", body=final_body)
    await mark_draft_sent(draft_id, final_body)

    return AiDraft(**{**draft.model_dump(), "body": final_body, "status": DraftStatus.SENT})


@router.post("/{draft_id}/reject", response_model=AiDraft)
async def reject_draft(draft_id: UUID, body: DraftReject, user: User = Depends(get_current_user)) -> AiDraft:
    draft, _session = await _get_accessible_draft(draft_id, user)
    if draft.status != DraftStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft already actioned")

    await mark_draft_rejected(draft_id, body.reason)
    return AiDraft(**{**draft.model_dump(), "status": DraftStatus.REJECTED, "rejection_reason": body.reason})


async def _get_accessible_draft(draft_id: UUID, user: User) -> tuple[AiDraft, Session]:
    draft = await get_draft(draft_id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Draft not found")
    session = await assert_session_access(user, draft.session_id)
    return draft, session
