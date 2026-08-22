"""One-time Drive backfill for the four pre-existing folders a tenant may
have accumulated before CoachFlow existed: calendar events exported as JSON,
the GROW/ICF context library, prior client notes, and meeting transcripts.

This is deliberately separate from the ongoing ingestion paths — live
Calendar API polling (calendar_scanner.py) and the single-file Drive-inbox
webhook (api/routes/webhooks.py) — which keep running unchanged after a
backfill completes. Each import_* function here writes one `import_jobs` row
and one `import_items` row per file it looked at, so an admin can watch
progress and manually resolve a file whose per-client subfolder didn't match
a client (see resolve_import_item).
"""
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.repository import (
    get_client_by_id,
    get_import_item,
    get_import_item_by_file,
    get_supabase,
    list_clients_for_tenant,
    record_import_item,
    row_of,
    rows_of,
    update_import_item,
    update_import_job_progress,
)
from app.integrations.google.drive import download_file, list_folder_contents, list_subfolders
from app.models.client import Client as ClientModel
from app.models.imports import ImportItemStatus, ImportJobStatus, ImportSource
from app.models.transcript import TranscriptSource
from app.services.calendar_scanner import add_working_days, match_session_type
from app.services.client_matching import (
    match_client_by_attendee_email as _match_client_by_attendee_email,
)
from app.services.client_matching import match_client_by_name as _match_client_by_name
from app.services.context_library_admin import create_context_library_entry_with_embedding
from app.services.document_extractor import extract_text
from app.services.transcript_normalizer import normalize
from app.session_types_generated import SESSION_TYPES

logger = logging.getLogger(__name__)


async def import_calendar_backfill(job_id: UUID, tenant_id: str, folder_id: str) -> None:
    """job_id is created synchronously by the route before this runs as a
    FastAPI BackgroundTask, so the client gets a job id back immediately
    instead of waiting for the whole backfill to finish."""
    try:
        files = [f for f in await list_folder_contents(tenant_id, folder_id) if f["name"].lower().endswith(".json")]
    except Exception as exc:
        logger.exception("Calendar backfill: could not list folder %s for tenant %s", folder_id, tenant_id)
        await update_import_job_progress(job_id, status=ImportJobStatus.FAILED, error_message=str(exc))
        return

    await update_import_job_progress(job_id, items_total=len(files))

    clients = await list_clients_for_tenant(tenant_id)
    reminder_rules = {
        row["session_type"]: row["lead_time_working_days"]
        for row in rows_of(get_supabase().table("reminder_rules").select("*").execute())
    }

    succeeded = 0
    failed = 0
    for file in files:
        existing = await get_import_item_by_file(tenant_id, ImportSource.CALENDAR, file["id"])
        if existing is not None:
            succeeded += existing["status"] == ImportItemStatus.IMPORTED.value
            failed += existing["status"] != ImportItemStatus.IMPORTED.value
            continue

        mime_type = file.get("mimeType", "application/json")
        try:
            events = parse_calendar_events(await download_file(tenant_id, file["id"]))
            unresolved = 0
            for event in events:
                resolved = await import_one_calendar_event(tenant_id, event, clients, reminder_rules)
                if not resolved:
                    unresolved += 1
            item_status = ImportItemStatus.IMPORTED if unresolved == 0 else ImportItemStatus.FAILED
            error = (
                None
                if unresolved == 0
                else f"{unresolved} of {len(events)} events matched a session type but no client could be resolved from attendees"
            )
            await record_import_item(job_id, tenant_id, ImportSource.CALENDAR, file["id"], file["name"], mime_type, item_status, error_message=error)
            succeeded += item_status == ImportItemStatus.IMPORTED
            failed += item_status != ImportItemStatus.IMPORTED
        except Exception as exc:
            logger.exception("Calendar backfill: failed to import %s", file["name"])
            await record_import_item(job_id, tenant_id, ImportSource.CALENDAR, file["id"], file["name"], mime_type, ImportItemStatus.FAILED, error_message=str(exc))
            failed += 1

        await update_import_job_progress(job_id, items_succeeded=succeeded, items_failed=failed)

    await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)


def parse_calendar_events(raw_bytes: bytes) -> list[dict[str, Any]]:
    """Assumes each JSON file matches the Google Calendar API event resource
    shape (summary/start/attendees), or a list/`{"items": [...]}` wrapper of
    them — the same shape integrations/google/calendar.py's live polling
    already consumes. Verify against a real exported file before running the
    production backfill; adjust here if the shape differs."""
    data = json.loads(raw_bytes)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "items" in data:
        return list(data["items"])
    return [data]


async def import_one_calendar_event(
    tenant_id: str, event: dict[str, Any], clients: list[ClientModel], reminder_rules: dict[str, int]
) -> bool:
    """Returns False only when the event matched a session-naming convention
    but no client could be resolved — sessions.client_id is NOT NULL, so
    there's nowhere valid to write it; a naming mismatch instead files to
    unmatched_events exactly like the live scanner and counts as handled."""
    summary = event.get("summary", "")
    start = event.get("start", {})
    start_raw = start.get("dateTime") or start.get("date")
    if not start_raw:
        return False
    event_date = datetime.fromisoformat(start_raw)

    session_type = match_session_type(summary)
    if session_type is None:
        get_supabase().table("unmatched_events").insert(
            {"tenant_id": tenant_id, "raw_event_summary": summary, "event_date": event_date.isoformat()}
        ).execute()
        return True

    client = _match_client_by_attendee_email(clients, event)
    if client is None:
        return False

    lead_time = reminder_rules.get(session_type.value, SESSION_TYPES[session_type].lead_time_working_days)
    trigger_date = add_working_days(event_date, lead_time)
    get_supabase().table("sessions").insert(
        {
            "client_id": str(client.id),
            "type": session_type.value,
            "tenant_id": tenant_id,
            "event_date": event_date.isoformat(),
            "trigger_date": trigger_date.isoformat(),
            "status": "upcoming",
        }
    ).execute()
    return True


async def import_context_library_backfill(job_id: UUID, tenant_id: str, folder_id: str) -> None:
    try:
        files = await list_folder_contents(tenant_id, folder_id)
    except Exception as exc:
        logger.exception("Context Library backfill: could not list folder %s for tenant %s", folder_id, tenant_id)
        await update_import_job_progress(job_id, status=ImportJobStatus.FAILED, error_message=str(exc))
        return

    await update_import_job_progress(job_id, items_total=len(files))

    succeeded = 0
    failed = 0
    for file in files:
        existing = await get_import_item_by_file(tenant_id, ImportSource.CONTEXT_LIBRARY, file["id"])
        if existing is not None:
            succeeded += existing["status"] == ImportItemStatus.IMPORTED.value
            failed += existing["status"] != ImportItemStatus.IMPORTED.value
            continue

        try:
            text = await extract_text(tenant_id, file["id"], file["mimeType"])
            await create_context_library_entry_with_embedding(None, file["name"], text)
            await record_import_item(job_id, tenant_id, ImportSource.CONTEXT_LIBRARY, file["id"], file["name"], file["mimeType"], ImportItemStatus.IMPORTED)
            succeeded += 1
        except Exception as exc:
            logger.exception("Context Library backfill: failed to import %s", file["name"])
            await record_import_item(
                job_id, tenant_id, ImportSource.CONTEXT_LIBRARY, file["id"], file["name"], file.get("mimeType", ""), ImportItemStatus.FAILED, error_message=str(exc)
            )
            failed += 1

        await update_import_job_progress(job_id, items_succeeded=succeeded, items_failed=failed)

    await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)


async def import_client_notes_backfill(job_id: UUID, tenant_id: str, folder_id: str) -> None:
    await _import_per_client_folder(job_id, tenant_id, folder_id, ImportSource.CLIENT_NOTES)


async def import_transcripts_backfill(job_id: UUID, tenant_id: str, folder_id: str) -> None:
    await _import_per_client_folder(job_id, tenant_id, folder_id, ImportSource.TRANSCRIPTS)


async def _import_per_client_folder(job_id: UUID, tenant_id: str, folder_id: str, source: ImportSource) -> None:
    """Shared walk for the two sources organized as one subfolder per client
    (per the coach's answer: client identity comes from matching the
    subfolder name to clients.name, with manual resolution via
    resolve_import_item for anything that doesn't match)."""
    try:
        clients = await list_clients_for_tenant(tenant_id)
        subfolders = await list_subfolders(tenant_id, folder_id)
        files_by_subfolder = [
            (_match_client_by_name(clients, subfolder["name"]), await list_folder_contents(tenant_id, subfolder["id"]))
            for subfolder in subfolders
        ]
    except Exception as exc:
        logger.exception("%s backfill: could not list folder %s for tenant %s", source.value, folder_id, tenant_id)
        await update_import_job_progress(job_id, status=ImportJobStatus.FAILED, error_message=str(exc))
        return

    await update_import_job_progress(job_id, items_total=sum(len(files) for _, files in files_by_subfolder))

    succeeded = 0
    failed = 0
    for client, files in files_by_subfolder:
        for file in files:
            existing = await get_import_item_by_file(tenant_id, source, file["id"])
            if existing is not None:
                succeeded += existing["status"] == ImportItemStatus.IMPORTED.value
                failed += existing["status"] != ImportItemStatus.IMPORTED.value
                continue

            if client is None:
                await record_import_item(
                    job_id, tenant_id, source, file["id"], file["name"], file["mimeType"],
                    ImportItemStatus.UNMATCHED_CLIENT,
                    error_message="No client name matches this file's subfolder",
                )
                failed += 1
            else:
                try:
                    if source == ImportSource.CLIENT_NOTES:
                        await _import_one_client_note(tenant_id, client, file)
                    else:
                        await _import_one_transcript(tenant_id, client, file)
                    await record_import_item(job_id, tenant_id, source, file["id"], file["name"], file["mimeType"], ImportItemStatus.IMPORTED, client_id=client.id)
                    succeeded += 1
                except Exception as exc:
                    logger.exception("%s backfill: failed to import %s", source.value, file["name"])
                    await record_import_item(
                        job_id, tenant_id, source, file["id"], file["name"], file.get("mimeType", ""), ImportItemStatus.FAILED, client_id=client.id, error_message=str(exc)
                    )
                    failed += 1

            await update_import_job_progress(job_id, items_succeeded=succeeded, items_failed=failed)

    await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)


async def _import_one_client_note(tenant_id: str, client: ClientModel, file: dict[str, Any]) -> None:
    text = await extract_text(tenant_id, file["id"], file["mimeType"])
    await create_context_library_entry_with_embedding(client.id, file["name"], text)


def _detect_transcript_source(file_name: str) -> TranscriptSource:
    file_name_lower = file_name.lower()
    return (
        TranscriptSource.GEMINI_MEET
        if file_name_lower.endswith(".json") or "gemini" in file_name_lower
        else TranscriptSource.PLAUD
    )


async def _import_one_transcript(tenant_id: str, client: ClientModel, file: dict[str, Any]) -> None:
    source = _detect_transcript_source(file["name"])
    raw_bytes = await download_file(tenant_id, file["id"])
    await insert_transcript_and_link(client, file["id"], source, raw_bytes, file.get("createdTime"))


async def insert_transcript_and_link(
    client: ClientModel,
    file_ref: str,
    source: TranscriptSource,
    raw_bytes: bytes,
    created_time_iso: str | None,
) -> None:
    """The Drive-independent core of transcript ingestion — normalize, insert
    into transcripts, best-effort link to the closest historical session.
    Shared with services/local_backfill.py, which reads bytes off disk
    instead of downloading them from Drive but needs the exact same
    insert/link behavior."""
    normalized = normalize(raw_bytes, source, attendee_names=[])

    result = (
        get_supabase()
        .table("transcripts")
        .insert(
            {
                "file_ref": file_ref,
                "source": source.value,
                "normalized_text": [segment.model_dump() for segment in normalized.segments],
                "parse_status": normalized.parse_status.value,
            }
        )
        .execute()
    )
    transcript_row = row_of(result)
    if transcript_row is None:
        return

    session = await _closest_session_for_client(client.id, created_time_iso)
    if session is not None:
        get_supabase().table("sessions").update({"transcript_id": transcript_row["id"]}).eq("id", session["id"]).execute()


async def _closest_session_for_client(client_id: UUID, reference_iso: str | None) -> dict[str, Any] | None:
    """Best-effort link back to the historical session this transcript
    belongs to, by nearest event_date — closes the linkage gap both
    webhooks.py and calendar_scanner.py leave as an explicit stub on the live
    path, at least for backfilled data."""
    if reference_iso is None:
        return None
    rows = rows_of(get_supabase().table("sessions").select("id, event_date").eq("client_id", str(client_id)).execute())
    if not rows:
        return None
    reference = datetime.fromisoformat(reference_iso)
    return min(rows, key=lambda row: abs(datetime.fromisoformat(row["event_date"]) - reference))


async def resolve_import_item(item_id: UUID, client_id: UUID) -> dict[str, Any]:
    """Manually assigns a client to a file recorded as unmatched_client (its
    subfolder name didn't match any client) and imports it. Only supports the
    two per-client-folder sources — calendar/context-library items are never
    written as unmatched_client in the first place."""
    item = await get_import_item(item_id)
    if item is None:
        raise LookupError(f"No import item {item_id}")
    client = await get_client_by_id(client_id)
    if client is None:
        raise LookupError(f"No client {client_id}")

    source = ImportSource(item["source"])
    file = {"id": item["drive_file_id"], "name": item["file_name"], "mimeType": item["mime_type"], "createdTime": None}

    try:
        if source == ImportSource.CLIENT_NOTES:
            await _import_one_client_note(item["tenant_id"], client, file)
        elif source == ImportSource.TRANSCRIPTS:
            await _import_one_transcript(item["tenant_id"], client, file)
        else:
            raise ValueError(f"Manual resolution isn't supported for source {source.value}")
    except Exception as exc:
        logger.exception("Failed to resolve import item %s to client %s", item_id, client_id)
        return await update_import_item(item_id, ImportItemStatus.FAILED, error_message=str(exc))

    return await update_import_item(item_id, ImportItemStatus.IMPORTED, client_id=client.id)
