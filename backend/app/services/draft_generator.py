"""Produces every client-facing artifact (reminder, summary, questionnaire,
prep email) — always stamped with the session's tenant_id, always written to
ai_drafts with status=pending. Nothing in this service ever calls Gmail
directly (backend/CLAUDE.md phase 5) — only POST /api/drafts/{id}/approve does.
"""
from uuid import UUID

from app.ai.gemini_client import generate
from app.db.repository import get_current_prompt_template, get_supabase, row_of
from app.models.draft import DraftType
from app.services.context_builder import build_context
from app.session_types_generated import SessionType


async def generate_prep_email_draft(session_id: UUID, client_id: UUID, tenant_id: str, session_type: SessionType) -> UUID:
    context = await build_context(client_id, session_type)
    template = await get_current_prompt_template(session_type, "pre")
    if template is None:
        raise RuntimeError(f"No current prompt template for {session_type.value}/pre")
    prompt = template["body"].format(**context.as_prompt_vars())

    result = await generate(prompt, structured=True)
    payload = result.as_json()
    body = _assemble_prep_email(payload)
    return _write_pending_draft(session_id, tenant_id, DraftType.PREP_EMAIL, body)


def _assemble_prep_email(payload: dict) -> str:
    bullets = "\n".join(f"- {point}" for point in payload["keypoints"])
    return f"{payload['greeting']}\n\n{payload['intro']}\n\n{bullets}\n\n{payload['signoff']}"


async def generate_summary_draft(session_id: UUID, tenant_id: str, client_summary: str) -> UUID:
    """Client-facing session summary — takes the already-generated
    client_summary from scorecard_generator so the same Gemini call isn't
    duplicated for post-session artifacts."""
    return _write_pending_draft(session_id, tenant_id, DraftType.SUMMARY, client_summary)


async def generate_reminder_draft(session_id: UUID, tenant_id: str, body: str) -> UUID:
    return _write_pending_draft(session_id, tenant_id, DraftType.REMINDER, body)


async def generate_questionnaire_draft(session_id: UUID, tenant_id: str, body: str) -> UUID:
    return _write_pending_draft(session_id, tenant_id, DraftType.QUESTIONNAIRE, body)


def _write_pending_draft(session_id: UUID, tenant_id: str, draft_type: DraftType, body: str) -> UUID:
    result = (
        get_supabase()
        .table("ai_drafts")
        .insert(
            {
                "session_id": str(session_id),
                "draft_type": draft_type.value,
                "tenant_id": tenant_id,
                "body": body,
                "status": "pending",
            }
        )
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return UUID(row["id"])
