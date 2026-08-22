from datetime import datetime
from enum import Enum
from uuid import UUID

from app.models.base import CamelModel


class ImportSource(str, Enum):
    CALENDAR = "calendar"
    CONTEXT_LIBRARY = "context_library"
    CLIENT_NOTES = "client_notes"
    TRANSCRIPTS = "transcripts"


class ImportJobStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportItemStatus(str, Enum):
    IMPORTED = "imported"
    FAILED = "failed"
    UNMATCHED_CLIENT = "unmatched_client"


class ImportJob(CamelModel):
    id: UUID
    tenant_id: str
    source: ImportSource
    status: ImportJobStatus
    items_total: int
    items_succeeded: int
    items_failed: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class ImportJobStart(CamelModel):
    tenant_id: str
    source: ImportSource
    folder_id: str


class ImportItem(CamelModel):
    id: UUID
    job_id: UUID
    tenant_id: str
    source: ImportSource
    drive_file_id: str
    file_name: str
    mime_type: str
    status: ImportItemStatus
    client_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime


class ImportItemResolve(CamelModel):
    client_id: UUID
