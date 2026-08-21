from enum import Enum
from uuid import UUID

from app.models.base import CamelModel


class DraftType(str, Enum):
    REMINDER = "reminder"
    SUMMARY = "summary"
    QUESTIONNAIRE = "questionnaire"
    PREP_EMAIL = "prep_email"


class DraftStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    REJECTED = "rejected"


class AiDraft(CamelModel):
    id: UUID
    session_id: UUID
    draft_type: DraftType
    tenant_id: str
    body: str
    status: DraftStatus
    rejection_reason: str | None = None


class DraftApprove(CamelModel):
    edited_body: str | None = None  # present when the coach used "Edit then approve"


class DraftReject(CamelModel):
    reason: str
