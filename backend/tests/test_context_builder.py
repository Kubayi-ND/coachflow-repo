"""app/services/context_builder.py — the ranked-retrieval rewrite. Mocks
Gemini embedding calls and Supabase per backend/CLAUDE.md testing notes."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services import context_builder
from app.session_types_generated import SESSION_TYPES, SessionType


class _FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._rows = [r for r in self._rows if r.get(key) == value]
        return self

    def is_(self, key, value):
        target = None if value == "null" else value
        self._rows = [r for r in self._rows if r.get(key) == target]
        return self

    def in_(self, key, values):
        self._rows = [r for r in self._rows if r.get(key) in values]
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._rows)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]], rpc_rows: list[dict] | None = None):
        self._tables = tables
        self._rpc_rows = rpc_rows or []
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name: str):
        return _FakeQuery(list(self._tables.get(name, [])))

    def rpc(self, name: str, params: dict):
        self.rpc_calls.append((name, params))
        return _FakeQuery(list(self._rpc_rows))


def _client_row(client_id):
    return {"id": str(client_id), "name": "Jane Doe"}


@pytest.mark.asyncio
async def test_pre_session_builds_synthetic_query_and_merges_org_wide_first():
    client_id = uuid4()
    org_wide = {"id": "org-1", "entry_group_id": "g1", "client_id": None, "title": "ICF Core", "body": "...", "version": 1}
    ranked_client_specific = {
        "id": "client-1",
        "entry_group_id": "g2",
        "client_id": str(client_id),
        "title": "Jane's goals",
        "body": "...",
        "version": 1,
    }
    fake_supabase = _FakeSupabase(
        tables={
            "clients": [_client_row(client_id)],
            "context_library_current": [org_wide],
            "sessions": [],
        },
        rpc_rows=[ranked_client_specific],
    )
    fake_embed = AsyncMock(return_value=[0.0] * 768)

    with (
        patch.object(context_builder, "get_supabase", return_value=fake_supabase),
        patch("app.db.repository.get_supabase", return_value=fake_supabase),
        patch.object(context_builder, "embed_query_text", new=fake_embed),
    ):
        result = await context_builder.build_context(client_id, SessionType.ONE_ON_ONE)

    query_text = fake_embed.call_args.args[0]
    assert SESSION_TYPES[SessionType.ONE_ON_ONE].label in query_text
    assert "Jane Doe" in query_text

    assert [row["id"] for row in result.context_library] == ["org-1", "client-1"]
    assert fake_supabase.rpc_calls[0][0] == "match_context_library"
    assert fake_supabase.rpc_calls[0][1]["filter_client_id"] == str(client_id)


@pytest.mark.asyncio
async def test_post_session_embeds_truncated_transcript_not_full_text():
    client_id = uuid4()
    long_transcript = ("A" * 5000) + "MIDDLE" + ("B" * 5000)
    fake_supabase = _FakeSupabase(
        tables={"clients": [_client_row(client_id)], "context_library_current": [], "sessions": []}
    )
    fake_embed = AsyncMock(return_value=[0.0] * 768)

    with (
        patch.object(context_builder, "get_supabase", return_value=fake_supabase),
        patch("app.db.repository.get_supabase", return_value=fake_supabase),
        patch.object(context_builder, "embed_query_text", new=fake_embed),
    ):
        await context_builder.build_context(client_id, SessionType.ONE_ON_ONE, transcript_text=long_transcript)

    query_text = fake_embed.call_args.args[0]
    assert len(query_text) < len(long_transcript)
    assert "MIDDLE" not in query_text  # truncated out of the middle
    assert query_text.startswith("A" * 100)
    assert query_text.endswith("B" * 100)


@pytest.mark.asyncio
async def test_prior_sessions_only_surface_sent_summaries():
    client_id = uuid4()
    session_with_sent_summary = {
        "id": "sess-1",
        "client_id": str(client_id),
        "type": "one_on_one",
        "status": "sent",
        "event_date": "2026-01-01",
    }
    session_with_pending_summary = {
        "id": "sess-2",
        "client_id": str(client_id),
        "type": "one_on_one",
        "status": "sent",
        "event_date": "2026-02-01",
    }
    fake_supabase = _FakeSupabase(
        tables={
            "clients": [_client_row(client_id)],
            "context_library_current": [],
            "sessions": [session_with_sent_summary, session_with_pending_summary],
            "ai_drafts": [
                {"session_id": "sess-1", "body": "Great progress on goal X.", "draft_type": "summary", "status": "sent"},
                {"session_id": "sess-2", "body": "Not yet approved.", "draft_type": "summary", "status": "pending"},
            ],
        }
    )
    fake_embed = AsyncMock(return_value=[0.0] * 768)

    with (
        patch.object(context_builder, "get_supabase", return_value=fake_supabase),
        patch("app.db.repository.get_supabase", return_value=fake_supabase),
        patch.object(context_builder, "embed_query_text", new=fake_embed),
    ):
        result = await context_builder.build_context(client_id, SessionType.ONE_ON_ONE)

    prior_sessions_text = result.as_prompt_vars()["prior_sessions"]
    assert "Great progress on goal X." in prior_sessions_text
    assert "Not yet approved." not in prior_sessions_text
    assert "no sent summary on file" in prior_sessions_text


@pytest.mark.asyncio
async def test_rows_outside_the_retrieval_scope_never_reach_the_prompt():
    """Defence in depth: even if the RPC or a query returned another client's
    entry or session, the scope check drops it before prompt assembly."""
    client_id = uuid4()
    other_client_id = uuid4()
    leaked_entry = {
        "id": "other-1", "entry_group_id": "g9", "client_id": str(other_client_id),
        "title": "Someone else's notes", "body": "PRIVATE", "version": 1,
    }
    leaked_session = {
        "id": "sess-x", "client_id": str(other_client_id), "type": "one_on_one",
        "status": "sent", "event_date": "2026-01-01",
    }
    fake_supabase = _FakeSupabase(
        tables={
            "clients": [_client_row(client_id)],
            "context_library_current": [],
            "sessions": [leaked_session],
            "ai_drafts": [],
        },
        rpc_rows=[leaked_entry],
    )
    fake_embed = AsyncMock(return_value=[0.0] * 768)

    with (
        patch.object(context_builder, "get_supabase", return_value=fake_supabase),
        patch("app.db.repository.get_supabase", return_value=fake_supabase),
        patch.object(context_builder, "embed_query_text", new=fake_embed),
    ):
        result = await context_builder.build_context(client_id, SessionType.ONE_ON_ONE)

    assert result.context_library == []
    assert result.prior_sessions == []
    assert "PRIVATE" not in "".join(result.as_prompt_vars().values())
