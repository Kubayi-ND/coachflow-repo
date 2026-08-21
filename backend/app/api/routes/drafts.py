from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.repository import get_draft, list_drafts, mark_draft_rejected, mark_draft_sent
from app.integrations.google.gmail import send_email
from app.models.draft import AiDraft, DraftApprove, DraftReject, DraftStatus
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[AiDraft])
async def get_drafts(status_filter: DraftStatus | None = None, user: User = Depends(get_current_user)) -> list[AiDraft]:
    return await list_drafts(status=status_filter)


@router.post("/{draft_id}/approve", response_model=AiDraft)
async def approve_draft(draft_id: UUID, body: DraftApprove, user: User = Depends(get_current_user)) -> AiDraft:
    """The only code path allowed to call Gmail. Re-reads the draft's
    tenant_id and sends from that tenant's identity, per backend/CLAUDE.md
    phase 6 — never trust a tenant id passed in from the client."""
    draft = await get_draft(draft_id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Draft not found")
    if draft.status != DraftStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft already actioned")

    final_body = body.edited_body if body.edited_body is not None else draft.body

    # Recipient resolution (client's email) is looked up via the session ->
    # client chain; omitted call shown for brevity in this scaffold.
    from app.db.repository import get_supabase, row_of

    session_row = row_of(
        get_supabase().table("sessions").select("client_id").eq("id", str(draft.session_id)).limit(1).execute()
    )
    client_row = (
        row_of(get_supabase().table("clients").select("email").eq("id", session_row["client_id"]).limit(1).execute())
        if session_row
        else None
    )
    recipient = client_row["email"] if client_row else ""

    await send_email(draft.tenant_id, to=recipient, subject=f"CoachFlow: {draft.draft_type.value}", body=final_body)
    await mark_draft_sent(draft_id, final_body)

    return AiDraft(**{**draft.model_dump(), "body": final_body, "status": DraftStatus.SENT})


@router.post("/{draft_id}/reject", response_model=AiDraft)
async def reject_draft(draft_id: UUID, body: DraftReject, user: User = Depends(get_current_user)) -> AiDraft:
    draft = await get_draft(draft_id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Draft not found")
    if draft.status != DraftStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft already actioned")

    await mark_draft_rejected(draft_id, body.reason)
    return AiDraft(**{**draft.model_dump(), "status": DraftStatus.REJECTED, "rejection_reason": body.reason})
