"""Integration test exercising context-build -> draft-generate end to end
against fixtures, mocking Gemini and Supabase per backend/CLAUDE.md's
testing notes ("CI must never make a live call to either").
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services import draft_generator
from app.session_types_generated import SessionType


class _FakeTable:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.inserted: list[dict] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def or_(self, *_args, **_kwargs):
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._rows)

    def insert(self, row: dict):
        self.inserted.append(row)
        return self


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = tables
        self.last_insert_table: str | None = None
        self.last_inserted_row: dict | None = None
        self._insert_result = [{"id": str(uuid4())}]

    def table(self, name: str):
        self.last_insert_table = name
        table = _FakeTable(self._tables.get(name, []))
        original_insert = table.insert

        def insert(row: dict):
            original_insert(row)
            self.last_inserted_row = row
            return MagicMock(execute=lambda: MagicMock(data=self._insert_result))

        table.insert = insert
        return table

    def rpc(self, _name: str, _params: dict):
        return _FakeTable([])


@pytest.mark.asyncio
async def test_generate_prep_email_draft_writes_pending_draft():
    fake_supabase = _FakeSupabase(
        tables={
            "clients": [{"id": "client-1", "name": "Jane Doe", "email": "jane@example.com"}],
            "context_library_current": [
                {"id": "ctx-1", "entry_group_id": "ctx-group-1", "title": "ICF Competency 3", "body": "...", "version": 1}
            ],
            "sessions": [],
            "prompt_templates_current": [
                {
                    "id": "tpl-1",
                    "entry_group_id": "tpl-group-1",
                    "session_type": "one_on_one",
                    "phase": "pre",
                    "title": "1-on-1 Executive Coaching — Pre-Session Prep",
                    "body": "prep prompt for {client_profile} {context_library} {prior_sessions}",
                    "version": 1,
                }
            ],
        }
    )

    with (
        patch("app.services.context_builder.get_supabase", return_value=fake_supabase),
        patch("app.services.draft_generator.get_supabase", return_value=fake_supabase),
        patch("app.db.repository.get_supabase", return_value=fake_supabase),
        patch("app.services.context_builder.embed_query_text", new=AsyncMock(return_value=[0.0] * 768)),
        patch(
            "app.services.draft_generator.generate",
            new=AsyncMock(
                return_value=MagicMock(
                    as_json=lambda: {
                        "greeting": "Hi Coach,",
                        "intro": "Here's what to know before your session.",
                        "keypoints": ["Open thread: budget approval", "Focus area: delegation"],
                        "signoff": "Best,\nCoachFlow",
                    },
                    tokens=42,
                    latency_ms=100,
                )
            ),
        ),
    ):
        draft_id = await draft_generator.generate_prep_email_draft(
            session_id=uuid4(), client_id=uuid4(), tenant_id="tenant_a", session_type=SessionType.ONE_ON_ONE
        )

    assert draft_id is not None
    assert fake_supabase.last_insert_table == "ai_drafts"
    body = fake_supabase.last_inserted_row["body"]
    assert "Hi Coach," in body
    assert "- Open thread: budget approval" in body
    assert "- Focus area: delegation" in body
    assert "Best,\nCoachFlow" in body
