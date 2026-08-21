from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import get_settings
from app.db.repository import get_supabase
from app.integrations.google.drive import download_file
from app.models.transcript import CalendarWebhookPayload, DriveWebhookPayload, TranscriptSource
from app.services.calendar_scanner import scan_tenant
from app.services.transcript_normalizer import normalize

router = APIRouter()


def _verify_secret(x_webhook_secret: str | None) -> None:
    if x_webhook_secret != get_settings().apps_script_webhook_shared_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")


@router.post("/drive")
async def drive_webhook(
    payload: DriveWebhookPayload, x_webhook_secret: str | None = Header(default=None)
) -> dict[str, str]:
    """New file landed in a tenant's Drive Inbox folder (backend/CLAUDE.md
    phase 2). Downloads it, tags source, files it, and normalizes it."""
    _verify_secret(x_webhook_secret)

    raw_bytes = await download_file(payload.tenant_id, payload.file_id)
    source = (
        TranscriptSource.GEMINI_MEET
        if payload.file_name.lower().endswith(".json") or "gemini" in payload.file_name.lower()
        else TranscriptSource.PLAUD
    )

    # Attendee-name resolution needs the matching calendar event, looked up by
    # file metadata/timing; omitted here — normalize() falls back to the raw
    # speaker labels from the source when no names are supplied.
    normalized = normalize(raw_bytes, source, attendee_names=[])

    get_supabase().table("transcripts").insert(
        {
            "file_ref": payload.file_id,
            "source": source.value,
            "normalized_text": [segment.model_dump() for segment in normalized.segments],
            "parse_status": normalized.parse_status.value,
        }
    ).execute()

    return {"status": "accepted"}


@router.post("/calendar")
async def calendar_webhook(
    payload: CalendarWebhookPayload, x_webhook_secret: str | None = Header(default=None)
) -> dict[str, str]:
    _verify_secret(x_webhook_secret)
    await scan_tenant(payload.tenant_id)
    return {"status": "accepted"}
