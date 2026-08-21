from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.db.repository import get_supabase, rows_of
from app.models.admin import MetricsSummary
from app.models.user import User

router = APIRouter()


@router.get("", response_model=MetricsSummary)
async def get_metrics(user: User = Depends(get_current_user)) -> MetricsSummary:
    """Aggregated KPIs for the Metrics view — an operations dashboard, not a
    report, per frontend/CLAUDE.md: summary tiles first, encode state (a
    falling approval-without-edits rate) as a visual flag on the frontend."""
    supabase = get_supabase()

    metrics_rows = rows_of(supabase.table("metrics_log").select("*").execute())
    total_cost = sum(float(row.get("gemini_cost_usd") or 0) for row in metrics_rows)

    drafts = rows_of(supabase.table("ai_drafts").select("status").execute())
    actioned = [d for d in drafts if d["status"] in ("sent", "rejected")]
    approved_without_edits = [d for d in actioned if d["status"] == "sent"]
    approval_rate = (len(approved_without_edits) / len(actioned)) if actioned else 0.0

    transcripts = rows_of(supabase.table("transcripts").select("source,parse_status").execute())
    parse_rates: dict[str, float] = {}
    for source in {t["source"] for t in transcripts}:
        source_rows = [t for t in transcripts if t["source"] == source]
        ok_rows = [t for t in source_rows if t["parse_status"] == "ok"]
        parse_rates[source] = (len(ok_rows) / len(source_rows)) if source_rows else 0.0

    unmatched_count = rows_of(
        supabase.table("unmatched_events").select("id").is_("resolved_session_type", "null").execute()
    )

    return MetricsSummary(
        hours_saved=0.0,  # derive from a per-workflow time estimate once instrumented
        avg_session_end_to_draft_ready_minutes=0.0,
        gemini_token_cost_usd=total_cost,
        billable_hour_value_protected_usd=0.0,
        transcript_parse_success_rate_by_source=parse_rates,
        draft_approval_rate_without_edits=approval_rate,
        unmatched_events_count=len(unmatched_count),
    )
