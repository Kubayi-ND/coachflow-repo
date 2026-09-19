"""Post-session ICF critique (services/post_session.py): what gets stored,
how grounding is checked, and that nothing is stored or sent on bad output.
Gemini and Supabase are mocked — CI never makes a live call."""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.icf_rubric import COMPETENCIES
from app.models.session import Session, SessionStatus
from app.services import post_session
from app.services.context_builder import AssembledContext
from app.session_types_generated import SessionType

LIBRARY_ID = "11111111-1111-1111-1111-111111111111"


def _session() -> Session:
    now = datetime.now(UTC)
    return Session(
        id=uuid4(), client_id=uuid4(), type=SessionType.ONE_ON_ONE, tenant_id="tenant_a",
        event_date=now, trigger_date=now, status=SessionStatus.UPCOMING,
    )


def _transcript(parse_status: str = "ok") -> dict:
    return {
        "id": str(uuid4()),
        "parse_status": parse_status,
        "normalized_text": [
            {"speaker": "Coach", "timestamp": "00:00:03", "text": "What would make this hour worthwhile?"},
            {"speaker": "Client", "timestamp": "00:00:09", "text": "Deciding how to raise it with my co-founder."},
        ],
    }


def _critique(**overrides) -> dict:
    competencies = []
    for competency in COMPETENCIES:
        competencies.append(
            {
                "id": competency.id, "name": competency.name, "rating": "meets_pcc", "summary": "ok",
                "evidence": [], "pcc_markers": [], "strengths": [], "growth_areas": [], "citations": [],
            }
        )
    # Competency 3: one real quote, one invented; one real citation, one
    # not in the prompt; one marker of its own, one from another competency.
    competencies[2].update(
        evidence=[
            {"quote": "What would make this hour worthwhile?", "line": 1, "speaker": "Coach"},
            {"quote": "Tell me about your childhood", "line": 2, "speaker": "Coach"},
        ],
        citations=[LIBRARY_ID, "not-a-retrieved-id"],
        pcc_markers=[{"id": "3.1", "observed": True, "note": ""}, {"id": "7.6", "observed": True, "note": ""}],
    )
    scorecard = {
        "overall_alignment": {"rating": "meets_pcc", "summary": "Solid."},
        "competencies": competencies,
        "top_strengths": ["Clear agreement"],
        "top_growth_areas": ["More silence"],
        **overrides,
    }
    return {"scorecard": scorecard, "client_summary": "You explored how to raise it with your co-founder."}


def _context() -> AssembledContext:
    return AssembledContext(
        {"name": "Jane"}, [{"id": LIBRARY_ID, "title": "ICF CCs with PCC Markers", "body": "...", "version": 1}], []
    )


def _patches(session, transcript, payload, *, existing_scorecard=None, has_summary=False):
    supabase = MagicMock()
    result = MagicMock(tokens=1234, latency_ms=900)
    result.as_json.return_value = payload
    mocks = {
        "generate": AsyncMock(return_value=result),
        "summary": AsyncMock(),
    }
    ctx = [
        patch.object(post_session, "get_session_by_id", new=AsyncMock(return_value=session)),
        patch.object(post_session, "_latest_scorecard", return_value=existing_scorecard),
        patch.object(post_session, "_linked_transcript", return_value=transcript),
        patch.object(post_session, "get_current_prompt_template", new=AsyncMock(return_value={"body": "{icf_rubric}\n{transcript}"})),
        patch.object(post_session, "build_context", new=AsyncMock(return_value=_context())),
        patch.object(post_session, "generate", new=mocks["generate"]),
        patch.object(post_session, "get_supabase", return_value=supabase),
        patch.object(post_session, "_has_summary_draft", return_value=has_summary),
        patch.object(post_session, "generate_summary_draft", new=mocks["summary"]),
    ]
    return ctx, supabase, mocks


async def _run(ctx, session, **kwargs):
    for p in ctx:
        p.start()
    try:
        return await post_session.run_post_session_analysis(session.id, **kwargs)
    finally:
        for p in ctx:
            p.stop()


@pytest.mark.asyncio
async def test_valid_critique_is_grounded_stored_and_summary_drafted():
    session = _session()
    ctx, supabase, mocks = _patches(session, _transcript(), _critique())

    stored = await _run(ctx, session)

    assessment = stored["competencies"][2]
    assert assessment["citations"] == [LIBRARY_ID]  # the id that wasn't in the prompt is dropped
    assert [m["id"] for m in assessment["pcc_markers"]] == ["3.1"]  # 7.6 belongs to competency 7
    assert [e["verified"] for e in assessment["evidence"]] == [True, False]  # invented quote flagged
    assert stored["transcript_unverified"] is False

    scorecard_row = supabase.table.return_value.insert.call_args_list[0].args[0]
    assert scorecard_row["citations"] == [{"context_id": LIBRARY_ID, "title": "ICF CCs with PCC Markers"}]
    mocks["summary"].assert_awaited_once()
    assert mocks["summary"].call_args.args[2] == "You explored how to raise it with your co-founder."


@pytest.mark.asyncio
async def test_prompt_gets_the_rubric_and_numbered_transcript():
    session = _session()
    ctx, _supabase, mocks = _patches(session, _transcript(), _critique())

    await _run(ctx, session)

    prompt = mocks["generate"].call_args.args[0]
    assert "7.6: Asks clear, direct, open questions" in prompt
    assert "L1 [00:00:03] Coach: What would make this hour worthwhile?" in prompt


@pytest.mark.asyncio
async def test_partial_transcript_is_flagged_unverified():
    session = _session()
    ctx, _supabase, mocks = _patches(session, _transcript("partial"), _critique())

    stored = await _run(ctx, session)

    assert stored["transcript_unverified"] is True
    assert "only partly parsed" in mocks["generate"].call_args.args[0]


@pytest.mark.asyncio
async def test_existing_summary_draft_is_not_duplicated():
    session = _session()
    ctx, _supabase, mocks = _patches(session, _transcript(), _critique(), has_summary=True)

    await _run(ctx, session, force=True)

    mocks["summary"].assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_output_stores_nothing_and_drafts_nothing():
    session = _session()
    bad = _critique()
    bad["scorecard"]["competencies"] = bad["scorecard"]["competencies"][:5]  # missing competencies
    ctx, supabase, mocks = _patches(session, _transcript(), bad)

    with pytest.raises(post_session.PostSessionError) as exc_info:
        await _run(ctx, session)

    assert exc_info.value.reason == "invalid_output"
    supabase.table.assert_not_called()
    mocks["summary"].assert_not_awaited()


@pytest.mark.asyncio
async def test_no_transcript_is_a_clear_error_without_calling_gemini():
    session = _session()
    ctx, _supabase, mocks = _patches(session, None, _critique())

    with pytest.raises(post_session.PostSessionError) as exc_info:
        await _run(ctx, session)

    assert exc_info.value.reason == "no_transcript"
    mocks["generate"].assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_critique_is_reused_unless_forced():
    session = _session()
    existing = {"structured_critique": {"rubric_version": "icf-pcc-v1"}}
    ctx, _supabase, mocks = _patches(session, _transcript(), _critique(), existing_scorecard=existing)

    stored = await _run(ctx, session)

    assert stored == {"rubric_version": "icf-pcc-v1"}
    mocks["generate"].assert_not_awaited()


@pytest.mark.asyncio
async def test_background_trigger_never_raises():
    with patch.object(post_session, "run_post_session_analysis", new=AsyncMock(side_effect=RuntimeError("boom"))):
        await post_session.analyse_linked_session(uuid4())


def test_payload_fixture_is_json_serialisable():
    json.dumps(_critique())
