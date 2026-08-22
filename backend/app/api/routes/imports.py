from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.security import require_admin
from app.db.repository import create_import_job, get_import_job, list_import_items, list_import_jobs
from app.models.imports import (
    ImportItem,
    ImportItemResolve,
    ImportJob,
    ImportJobStart,
    ImportSource,
)
from app.models.user import User
from app.services import drive_backfill

router = APIRouter()

_BACKFILL_FUNCTIONS = {
    ImportSource.CALENDAR: drive_backfill.import_calendar_backfill,
    ImportSource.CONTEXT_LIBRARY: drive_backfill.import_context_library_backfill,
    ImportSource.CLIENT_NOTES: drive_backfill.import_client_notes_backfill,
    ImportSource.TRANSCRIPTS: drive_backfill.import_transcripts_backfill,
}


@router.post("", response_model=ImportJob, status_code=status.HTTP_202_ACCEPTED)
async def start_import(body: ImportJobStart, background_tasks: BackgroundTasks, user: User = Depends(require_admin)) -> ImportJob:
    """Creates the job row synchronously (so the response carries a real job
    id) and runs the actual backfill as a background task — the Admin >
    Import page polls GET /api/admin/imports for progress."""
    job = await create_import_job(body.tenant_id, body.source)
    background_tasks.add_task(_BACKFILL_FUNCTIONS[body.source], UUID(job["id"]), body.tenant_id, body.folder_id)
    return ImportJob(**job)


@router.get("", response_model=list[ImportJob])
async def get_import_jobs(tenant_id: str | None = None, user: User = Depends(require_admin)) -> list[ImportJob]:
    rows = await list_import_jobs(tenant_id)
    return [ImportJob(**row) for row in rows]


@router.get("/{job_id}", response_model=ImportJob)
async def get_import_job_route(job_id: UUID, user: User = Depends(require_admin)) -> ImportJob:
    row = await get_import_job(job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import job not found")
    return ImportJob(**row)


@router.get("/{job_id}/items", response_model=list[ImportItem])
async def get_import_job_items(job_id: UUID, user: User = Depends(require_admin)) -> list[ImportItem]:
    rows = await list_import_items(job_id)
    return [ImportItem(**row) for row in rows]


@router.post("/items/{item_id}/resolve", response_model=ImportItem)
async def resolve_import_item_route(item_id: UUID, body: ImportItemResolve, user: User = Depends(require_admin)) -> ImportItem:
    """Manually assigns a client to a file whose per-client subfolder didn't
    match one (frontend/CLAUDE.md-style one-click resolution, mirroring the
    Calendar view's unmatched-events flow)."""
    try:
        row = await drive_backfill.resolve_import_item(item_id, body.client_id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ImportItem(**row)
