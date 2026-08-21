from enum import Enum
from typing import Any
from uuid import UUID

from app.models.base import CamelModel


class TranscriptSource(str, Enum):
    PLAUD = "plaud"
    GEMINI_MEET = "gemini_meet"


class ParseStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class TranscriptSegment(CamelModel):
    speaker: str
    timestamp: str
    text: str


class Transcript(CamelModel):
    id: UUID
    file_ref: str
    source: TranscriptSource
    normalized_text: list[TranscriptSegment] | None = None
    parse_status: ParseStatus


class DriveWebhookPayload(CamelModel):
    tenant_id: str
    file_id: str
    file_name: str
    mime_type: str


class CalendarWebhookPayload(CamelModel):
    tenant_id: str
    raw: dict[str, Any] | None = None
