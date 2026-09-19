"""Post-session analysis: an internal ICF critique of the coach's performance
plus a client-facing summary draft, from one Gemini call (backend/CLAUDE.md
phase 5).

- The critique is coach-only. It is stored in `scorecards`, never emailed,
  and scored against the fixed rubric in ai/icf_rubric.py.
- The client summary goes to the Approvals inbox as a pending `ai_drafts`
  row. Nothing here sends anything.

Grounding is checked before anything is stored:
- citations must be Context Library rows that were actually in the prompt;
- evidence quotes must appear in the transcript (flagged, not dropped, when
  they don't);
- PCC marker ids must belong to the competency they're filed under.

Triggered manually (POST /api/sessions/{id}/analysis) and automatically when
a transcript is linked to a session (analyse_linked_session).
"""
import json
import logging
import re
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.ai.gemini_client import generate
from app.ai.icf_rubric import COMPETENCIES, render_rubric
from app.ai.prompt_render import render_prompt
from app.db.repository import (
    get_current_prompt_template,
    get_session_by_id,
    get_supabase,
    row_of,
    rows_of,
)
from app.models.draft import DraftType
from app.models.scorecard import IcfCritique, PostSessionOutput
from app.models.session import Session
from app.models.transcript import ParseStatus, TranscriptSegment
from app.services.context_builder import build_context
from app.services.draft_generator import generate_summary_draft
from app.services.transcript_normalizer import segments_to_text

logger = logging.getLogger(__name__)

_MARKERS_BY_COMPETENCY = {c.id: {marker_id for marker_id, _ in c.markers} for c in COMPETENCIES}
_UNVERIFIED_NOTE = (
    "NOTE: this transcript only partly parsed (missing or garbled lines). Rate only what is "
    "clearly evidenced, and say where the gaps limit the assessment."
)


class PostSessionError(Exception):
    """A session can't be analysed. `reason` is a stable code the route
    maps to an HTTP status: no_transcript, transcript_unusable,
    no_template, invalid_output."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


async def run_post_session_analysis(session_id: UUID, *, force: bool = False) -> dict[str, Any]:
    """Returns the stored critique. Without `force`, an existing critique is
    returned as-is and Gemini isn't called."""
    session = await get_session_by_id(session_id)
    if session is None:
        raise PostSessionError("no_transcript", "Session not found")

    if not force:
        existing = _latest_scorecard(session.id)
        if existing is not None:
            return dict(existing["structured_critique"])

    transcript = _linked_transcript(session)
    if transcript is None:
        raise PostSessionError("no_transcript", "No transcript is linked to this session yet")
    segments = [TranscriptSegment(**segment) for segment in transcript.get("normalized_text") or []]
    if transcript.get("parse_status") == ParseStatus.FAILED.value or not segments:
        raise PostSessionError("transcript_unusable", "The linked transcript couldn't be read")
    unverified = transcript.get("parse_status") == ParseStatus.PARTIAL.value

    template = await get_current_prompt_template(session.type, "post")
    if template is None:
        raise PostSessionError("no_template", f"No post-session prompt for {session.type.value}")

    plain_transcript = "\n".join(segment.text for segment in segments)
    context = await build_context(
        session.client_id, session.type, exclude_session_id=session.id, transcript_text=plain_transcript
    )
    numbered = segments_to_text(segments)
    prompt = render_prompt(
        template["body"],
        {
            **context.as_prompt_vars(),
            "transcript": f"{_UNVERIFIED_NOTE}\n\n{numbered}" if unverified else numbered,
            "icf_rubric": render_rubric(),
        },
    )

    result = await generate(prompt, structured=True)
    try:
        output = PostSessionOutput.model_validate(result.as_json())
    except (ValidationError, json.JSONDecodeError) as exc:
        # Don't log the output itself — it quotes the client's transcript.
        logger.warning("Post-session output for session %s failed validation: %s", session.id, type(exc).__name__)
        raise PostSessionError("invalid_output", "The AI returned an unusable critique; try again") from exc

    critique, citations = _ground(output.scorecard, context.context_library, segments)
    critique.transcript_unverified = unverified
    stored = critique.model_dump(mode="json")

    supabase = get_supabase()
    supabase.table("scorecards").delete().eq("session_id", str(session.id)).execute()
    supabase.table("scorecards").insert(
        {"session_id": str(session.id), "structured_critique": stored, "citations": citations}
    ).execute()
    supabase.table("metrics_log").insert(
        {"session_id": str(session.id), "gemini_tokens": result.tokens, "gemini_latency_ms": result.latency_ms}
    ).execute()

    if not _has_summary_draft(session.id):
        await generate_summary_draft(session.id, session.tenant_id, output.client_summary)
    return stored


async def analyse_linked_session(session_id: UUID) -> None:
    """Background trigger after a transcript is linked. Never raises: a
    failed analysis must not break an import or a webhook, and the coach
    can always run it again from the dashboard."""
    try:
        await run_post_session_analysis(session_id)
    except PostSessionError as exc:
        logger.info("Post-session analysis skipped for session %s: %s", session_id, exc.reason)
    except Exception:
        logger.exception("Post-session analysis failed for session %s", session_id)


def _ground(
    critique: IcfCritique, context_rows: list[dict[str, Any]], segments: list[TranscriptSegment]
) -> tuple[IcfCritique, list[dict[str, str]]]:
    titles = {str(row["id"]): row.get("title", "") for row in context_rows}
    transcript_text = _normalise(" ".join(segment.text for segment in segments))
    cited: dict[str, str] = {}

    for assessment in critique.competencies:
        assessment.citations = [cid for cid in assessment.citations if cid in titles]
        cited.update({cid: titles[cid] for cid in assessment.citations})
        allowed = _MARKERS_BY_COMPETENCY[assessment.id]
        assessment.pcc_markers = [marker for marker in assessment.pcc_markers if marker.id in allowed]
        for evidence in assessment.evidence:
            quote = _normalise(evidence.quote)
            evidence.verified = bool(quote) and quote in transcript_text

    return critique, [{"context_id": cid, "title": title} for cid, title in cited.items()]


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


def _latest_scorecard(session_id: UUID) -> dict[str, Any] | None:
    return row_of(
        get_supabase()
        .table("scorecards")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )


def _linked_transcript(session: Session) -> dict[str, Any] | None:
    query = get_supabase().table("transcripts").select("*")
    if session.transcript_id is not None:
        return row_of(query.eq("id", str(session.transcript_id)).limit(1).execute())
    return row_of(query.eq("session_id", str(session.id)).order("created_at", desc=True).limit(1).execute())


def _has_summary_draft(session_id: UUID) -> bool:
    rows = rows_of(
        get_supabase()
        .table("ai_drafts")
        .select("id,status")
        .eq("session_id", str(session_id))
        .eq("draft_type", DraftType.SUMMARY.value)
        .execute()
    )
    return any(row["status"] in ("pending", "sent") for row in rows)
