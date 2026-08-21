from app.models.base import CamelModel
from app.session_types_generated import SessionType


class ReminderRule(CamelModel):
    session_type: SessionType
    lead_time_working_days: int
    naming_pattern: str


class PromptTemplate(CamelModel):
    session_type: SessionType
    phase: str  # "pre" | "post"
    body: str
    version: int = 1


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
