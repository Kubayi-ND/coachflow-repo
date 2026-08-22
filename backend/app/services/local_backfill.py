"""One-time local-file backfill — pushes pre-existing coaching material
straight into Supabase from local disk instead of Google Drive, for a tenant
whose OAuth isn't connected yet. A full replacement (per the coach's answer)
for the Drive-based backfill (services/drive_backfill.py) for this specific
batch of data — the Drive path stays as-is for anything imported later once
OAuth is wired up.

Reuses drive_backfill.py's Drive-independent logic directly rather than
duplicating it: parse_calendar_events/import_one_calendar_event (already
operate on plain bytes/dict, no Drive calls) and insert_transcript_and_link
(the normalize-insert-link core, split out of Drive's transcript path
specifically so this module could share it). Client-notes ingestion needs no
shared extraction step — local .md files are already plain text, so this
module calls create_context_library_entry_with_embedding directly.

Directory convention (see data/local_backfill/README.md):
    <upload_dir>/
    ├── context-library/*.md   org-wide GROW/ICF docs, no frontmatter needed
    ├── client-notes/*.md      frontmatter: client: <Name matching clients.name>
    ├── transcripts/*.md       frontmatter: client: <Name>; optional date:, source:
    └── calendar/*.json        Google Calendar API event resource shape

Any category subdirectory may be missing — reported as 0 files, not an error.

Dry run (the default the CLI script uses) reads clients/import-item state
from Supabase to give an accurate preview (e.g. which client names actually
match), but performs zero writes — no job/item rows, no context_library/
transcripts/sessions/unmatched_events inserts.
"""
import logging
from pathlib import Path
from uuid import UUID

from app.db.repository import (
    create_import_job,
    get_import_item_by_file,
    get_supabase,
    list_clients_for_tenant,
    record_import_item,
    rows_of,
    update_import_job_progress,
)
from app.models.client import Client as ClientModel
from app.models.imports import ImportItemStatus, ImportJobStatus, ImportSource
from app.models.transcript import TranscriptSource
from app.services.client_matching import match_client_by_name
from app.services.context_library_admin import create_context_library_entry_with_embedding
from app.services.document_extractor import extract_local_file_text
from app.services.drive_backfill import (
    import_one_calendar_event,
    insert_transcript_and_link,
    parse_calendar_events,
)

logger = logging.getLogger(__name__)

CONTEXT_LIBRARY_DIRNAME = "context-library"
UPLOADED_CONTEXT_LIBRARY_DIRNAME = "Grow Context Library"
CLIENT_NOTES_DIRNAME = "client-notes"
TRANSCRIPTS_DIRNAME = "transcripts"
CALENDAR_DIRNAME = "calendar"

_MARKDOWN_MIME_TYPE = "text/markdown"
_JSON_MIME_TYPE = "application/json"
_CONTEXT_LIBRARY_SUFFIXES = {".docx", ".md", ".pdf", ".txt"}
_PROMPT_DOCUMENT_NAMES = {
    "coaching preparation prompt.docx",
    "coaching evaluation prompt.docx",
}


async def run_local_backfill(
    tenant_id: str, upload_dir: Path, *, sources: set[ImportSource] | None = None, dry_run: bool = True
) -> dict[ImportSource, dict[str, int]]:
    """Orchestrator the CLI script calls. Runs calendar before transcripts
    within one invocation, since transcript linking looks up existing
    `sessions` rows for the closest-date match."""
    wanted = sources or set(ImportSource)
    results: dict[ImportSource, dict[str, int]] = {}

    if ImportSource.CALENDAR in wanted:
        results[ImportSource.CALENDAR] = await import_local_calendar(
            tenant_id, upload_dir / CALENDAR_DIRNAME, upload_dir, dry_run=dry_run
        )
    if ImportSource.CONTEXT_LIBRARY in wanted:
        context_library_dir = upload_dir / CONTEXT_LIBRARY_DIRNAME
        uploaded_context_library_dir = upload_dir / UPLOADED_CONTEXT_LIBRARY_DIRNAME
        if not context_library_dir.is_dir() and uploaded_context_library_dir.is_dir():
            context_library_dir = uploaded_context_library_dir
        results[ImportSource.CONTEXT_LIBRARY] = await import_local_context_library(
            tenant_id, context_library_dir, upload_dir, dry_run=dry_run
        )
    if ImportSource.CLIENT_NOTES in wanted:
        results[ImportSource.CLIENT_NOTES] = await import_local_client_notes(
            tenant_id, upload_dir / CLIENT_NOTES_DIRNAME, upload_dir, dry_run=dry_run
        )
    if ImportSource.TRANSCRIPTS in wanted:
        results[ImportSource.TRANSCRIPTS] = await import_local_transcripts(
            tenant_id, upload_dir / TRANSCRIPTS_DIRNAME, upload_dir, dry_run=dry_run
        )
    return results


def _empty_counts(total: int = 0) -> dict[str, int]:
    return {"total": total, "succeeded": 0, "failed": 0, "unmatched": 0}


def _tally(counts: dict[str, int], status_value: str) -> None:
    if status_value == ImportItemStatus.IMPORTED.value:
        counts["succeeded"] += 1
    elif status_value == ImportItemStatus.UNMATCHED_CLIENT.value:
        counts["unmatched"] += 1
    else:
        counts["failed"] += 1


def _relative_file_id(path: Path, upload_dir: Path) -> str:
    return path.relative_to(upload_dir).as_posix()


def _parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    """Splits a leading `---\\nkey: value\\n---\\n` block, if present, from the
    body. Only supports flat, unquoted `key: value` pairs, one per line —
    sufficient for client:/title:/date:/source:. Returns ({}, raw_text)
    unchanged if the file has no frontmatter block."""
    if not raw_text.startswith("---"):
        return {}, raw_text

    lines = raw_text.splitlines()
    closing_index = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if closing_index is None:
        return {}, raw_text

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()

    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return frontmatter, body


def _as_aware_iso(raw_date: str) -> str:
    """A bare `date: 2026-01-10` frontmatter value has no timezone, but
    _closest_session_for_client compares it against timestamptz session rows
    — subtracting a naive from an aware datetime raises TypeError. Normalize
    to midnight UTC unless the value already looks like a full datetime."""
    return raw_date if "T" in raw_date else f"{raw_date}T00:00:00+00:00"


async def import_local_calendar(tenant_id: str, dir_path: Path, upload_dir: Path, *, dry_run: bool) -> dict[str, int]:
    if not dir_path.is_dir():
        return _empty_counts()

    files = sorted(dir_path.glob("*.json"))
    counts = _empty_counts(len(files))
    if not files:
        return counts

    if dry_run:
        for file in files:
            try:
                events = parse_calendar_events(file.read_bytes())
                print(f"[dry-run] calendar: {file.name} - {len(events)} event(s)")
                counts["succeeded"] += 1
            except Exception as exc:
                logger.exception("Dry-run: failed to parse %s", file.name)
                print(f"[dry-run] calendar: {file.name} - FAILED to parse ({exc})")
                counts["failed"] += 1
        return counts

    job_id = UUID((await create_import_job(tenant_id, ImportSource.CALENDAR))["id"])
    await update_import_job_progress(job_id, items_total=len(files))

    clients = await list_clients_for_tenant(tenant_id)
    reminder_rules = {
        row["session_type"]: row["lead_time_working_days"]
        for row in rows_of(get_supabase().table("reminder_rules").select("*").execute())
    }

    for file in files:
        rel_id = _relative_file_id(file, upload_dir)
        existing = await get_import_item_by_file(tenant_id, ImportSource.CALENDAR, rel_id)
        if existing is not None:
            _tally(counts, existing["status"])
            continue

        try:
            events = parse_calendar_events(file.read_bytes())
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
            await record_import_item(job_id, tenant_id, ImportSource.CALENDAR, rel_id, file.name, _JSON_MIME_TYPE, item_status, error_message=error)
            _tally(counts, item_status.value)
        except Exception as exc:
            logger.exception("Local calendar backfill: failed to import %s", file.name)
            await record_import_item(job_id, tenant_id, ImportSource.CALENDAR, rel_id, file.name, _JSON_MIME_TYPE, ImportItemStatus.FAILED, error_message=str(exc))
            counts["failed"] += 1

        await update_import_job_progress(job_id, items_succeeded=counts["succeeded"], items_failed=counts["failed"] + counts["unmatched"])

    await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)
    return counts


async def import_local_context_library(tenant_id: str, dir_path: Path, upload_dir: Path, *, dry_run: bool) -> dict[str, int]:
    if not dir_path.is_dir():
        return _empty_counts()

    files = sorted(
        path
        for path in dir_path.iterdir()
        if path.is_file()
        and path.suffix.lower() in _CONTEXT_LIBRARY_SUFFIXES
        and path.name.casefold() not in _PROMPT_DOCUMENT_NAMES
    )
    counts = _empty_counts(len(files))
    if not files:
        return counts

    if dry_run:
        for file in files:
            raw_text = extract_local_file_text(file)
            frontmatter, body = _parse_frontmatter(raw_text)
            title = frontmatter.get("title", file.stem)
            print(f"[dry-run] context-library: {file.name} - title={title!r}, {len(body)} chars")
            counts["succeeded"] += 1
        return counts

    job_id = UUID((await create_import_job(tenant_id, ImportSource.CONTEXT_LIBRARY))["id"])
    await update_import_job_progress(job_id, items_total=len(files))

    for file in files:
        rel_id = _relative_file_id(file, upload_dir)
        existing = await get_import_item_by_file(tenant_id, ImportSource.CONTEXT_LIBRARY, rel_id)
        if existing is not None:
            _tally(counts, existing["status"])
            continue

        try:
            raw_text = extract_local_file_text(file)
            frontmatter, body = _parse_frontmatter(raw_text)
            title = frontmatter.get("title", file.stem)
            await create_context_library_entry_with_embedding(None, title, body)
            await record_import_item(job_id, tenant_id, ImportSource.CONTEXT_LIBRARY, rel_id, file.name, _MARKDOWN_MIME_TYPE, ImportItemStatus.IMPORTED)
            counts["succeeded"] += 1
        except Exception as exc:
            logger.exception("Local context-library backfill: failed to import %s", file.name)
            await record_import_item(job_id, tenant_id, ImportSource.CONTEXT_LIBRARY, rel_id, file.name, _MARKDOWN_MIME_TYPE, ImportItemStatus.FAILED, error_message=str(exc))
            counts["failed"] += 1

        await update_import_job_progress(job_id, items_succeeded=counts["succeeded"], items_failed=counts["failed"] + counts["unmatched"])

    await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)
    return counts


async def import_local_client_notes(tenant_id: str, dir_path: Path, upload_dir: Path, *, dry_run: bool) -> dict[str, int]:
    return await _import_local_per_client_files(tenant_id, dir_path, upload_dir, ImportSource.CLIENT_NOTES, dry_run=dry_run)


async def import_local_transcripts(tenant_id: str, dir_path: Path, upload_dir: Path, *, dry_run: bool) -> dict[str, int]:
    return await _import_local_per_client_files(tenant_id, dir_path, upload_dir, ImportSource.TRANSCRIPTS, dry_run=dry_run)


async def _import_local_per_client_files(
    tenant_id: str, dir_path: Path, upload_dir: Path, source: ImportSource, *, dry_run: bool
) -> dict[str, int]:
    """Shared walk for the two markdown sources keyed by a `client:`
    frontmatter field — same match_client_by_name semantics the Drive path
    uses for its per-client subfolders, just fed a frontmatter value instead
    of a folder name."""
    if not dir_path.is_dir():
        return _empty_counts()

    files = sorted(dir_path.glob("*.md"))
    counts = _empty_counts(len(files))
    if not files:
        return counts

    clients = await list_clients_for_tenant(tenant_id)

    job_id: UUID | None = None
    if not dry_run:
        job_id = UUID((await create_import_job(tenant_id, source))["id"])
        await update_import_job_progress(job_id, items_total=len(files))

    for file in files:
        frontmatter, body = _parse_frontmatter(file.read_text(encoding="utf-8"))
        client_name = frontmatter.get("client", "")
        client = match_client_by_name(clients, client_name) if client_name else None

        if dry_run:
            label = client.name if client is not None else f"UNMATCHED ({client_name!r})"
            print(f"[dry-run] {source.value}: {file.name} - client={label}")
            counts["succeeded" if client is not None else "unmatched"] += 1
            continue

        assert job_id is not None
        rel_id = _relative_file_id(file, upload_dir)
        existing = await get_import_item_by_file(tenant_id, source, rel_id)
        if existing is not None:
            _tally(counts, existing["status"])
            continue

        if client is None:
            error = f"No client named {client_name!r}" if client_name else "Missing 'client:' frontmatter field"
            await record_import_item(job_id, tenant_id, source, rel_id, file.name, _MARKDOWN_MIME_TYPE, ImportItemStatus.UNMATCHED_CLIENT, error_message=error)
            counts["unmatched"] += 1
        else:
            try:
                await _insert_one_local_file(source, client, file, rel_id, frontmatter, body)
                await record_import_item(job_id, tenant_id, source, rel_id, file.name, _MARKDOWN_MIME_TYPE, ImportItemStatus.IMPORTED, client_id=client.id)
                counts["succeeded"] += 1
            except Exception as exc:
                logger.exception("Local %s backfill: failed to import %s", source.value, file.name)
                await record_import_item(job_id, tenant_id, source, rel_id, file.name, _MARKDOWN_MIME_TYPE, ImportItemStatus.FAILED, client_id=client.id, error_message=str(exc))
                counts["failed"] += 1

        await update_import_job_progress(job_id, items_succeeded=counts["succeeded"], items_failed=counts["failed"] + counts["unmatched"])

    if job_id is not None:
        await update_import_job_progress(job_id, status=ImportJobStatus.COMPLETED)
    return counts


async def _insert_one_local_file(
    source: ImportSource, client: ClientModel, file: Path, rel_id: str, frontmatter: dict[str, str], body: str
) -> None:
    if source == ImportSource.CLIENT_NOTES:
        title = frontmatter.get("title", file.stem)
        await create_context_library_entry_with_embedding(client.id, title, body)
        return

    source_override = frontmatter.get("source", "").strip().lower()
    transcript_source = TranscriptSource.GEMINI_MEET if source_override == "gemini_meet" else TranscriptSource.PLAUD
    raw_date = frontmatter.get("date", "").strip()
    created_time_iso = _as_aware_iso(raw_date) if raw_date else None
    await insert_transcript_and_link(client, rel_id, transcript_source, body.encode("utf-8"), created_time_iso)
