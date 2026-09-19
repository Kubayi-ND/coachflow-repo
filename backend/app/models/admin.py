from uuid import UUID

from app.models.base import CamelModel
from app.session_types_generated import SessionType


class ReminderRule(CamelModel):
    session_type: SessionType
    lead_time_working_days: int
    naming_pattern: str


class PromptTemplate(CamelModel):
    id: UUID
    entry_group_id: UUID
    session_type: SessionType
    phase: str  # "pre" | "post"
    title: str  # clear heading, e.g. "1-on-1 — Pre-Session Prep"
    description: str | None = None  # what it does, when it runs, what it produces
    body: str
    version: int
    created_at: str


class PromptTemplateCreate(CamelModel):
    session_type: SessionType
    phase: str
    title: str
    description: str | None = None
    body: str


class PromptTemplateVersion(CamelModel):
    title: str
    description: str | None = None  # omitted = keep the current version's description
    body: str


class TenantStatus(CamelModel):
    id: str
    workspace_domain: str
    connected: bool  # never returns the raw token


class MetricsSummary(CamelModel):
    hours_saved: float
    avg_session_end_to_draft_ready_minutes: float
    gemini_token_cost_usd: float
    billable_hour_value_protected_usd: float
    transcript_parse_success_rate_by_source: dict[str, float]
    draft_approval_rate_without_edits: float
    unmatched_events_count: int
