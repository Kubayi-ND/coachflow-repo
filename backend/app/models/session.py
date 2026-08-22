from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.models.base import CamelModel
from app.session_types_generated import SessionType


class SessionStatus(str, Enum):
    UPCOMING = "upcoming"
    PREP_GENERATING = "prep_generating"
    READY_FOR_REVIEW = "ready_for_review"
    SENT = "sent"


class Session(CamelModel):
    id: UUID
    client_id: UUID
    type: SessionType
    tenant_id: str
    event_date: datetime
    trigger_date: datetime
    transcript_id: UUID | None = None
    status: SessionStatus


class SessionHistoryItem(CamelModel):
    id: UUID
    event_date: datetime
    summary: str | None = None


class SessionPrep(CamelModel):
    session: Session
    prep: str
    scorecard: dict[str, object] | None = None
    citations: list[dict[str, object]] = Field(default_factory=list)
    history: list[SessionHistoryItem] = Field(default_factory=list)


class UnmatchedEvent(CamelModel):
    id: UUID
    tenant_id: str
    raw_event_summary: str
    event_date: datetime
    resolved_session_type: SessionType | None = None


class UnmatchedEventResolve(CamelModel):
    resolved_session_type: SessionType
