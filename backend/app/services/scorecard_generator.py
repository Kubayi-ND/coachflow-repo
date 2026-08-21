"""Produces the internal-only ICF/GROW critique. Never approval-gated — it's
internal, unlike everything in draft_generator.py (backend/CLAUDE.md phase 5).
"""
from typing import Any
from uuid import UUID

from app.ai.gemini_client import generate
from app.ai.prompts import annual_review, monthly_council, one_on_one_post, quarterly_review
from app.db.repository import get_supabase
from app.services.context_builder import build_context
from app.session_types_generated import SessionType

_POST_TEMPLATES = {
    SessionType.ONE_ON_ONE: one_on_one_post.TEMPLATE,
    SessionType.QUARTERLY_REVIEW: quarterly_review.POST_TEMPLATE,
    SessionType.ANNUAL_REVIEW: annual_review.POST_TEMPLATE,
    SessionType.MONTHLY_COUNCIL: monthly_council.POST_TEMPLATE,
}


async def generate_scorecard_and_summary(
    session_id: UUID, client_id: UUID, session_type: SessionType, transcript_text: str
) -> tuple[dict[str, Any], str]:
    context = await build_context(client_id, session_type, exclude_session_id=session_id)
    prompt = _POST_TEMPLATES[session_type].format(transcript=transcript_text, **context.as_prompt_vars())

    result = await generate(prompt, structured=True)
    payload = result.as_json()

    get_supabase().table("scorecards").insert(
        {
            "session_id": str(session_id),
            "structured_critique": payload["scorecard"],
            "citations": payload["scorecard"].get("citations", []),
        }
    ).execute()

    get_supabase().table("metrics_log").insert(
        {
            "session_id": str(session_id),
            "gemini_tokens": result.tokens,
            "gemini_latency_ms": result.latency_ms,
        }
    ).execute()

    return payload["scorecard"], payload["client_summary"]
