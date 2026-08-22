"""scripts/backfill_context_library_embeddings.py — asserts only rows with a
null embedding get updated, and the update payload carries the computed
embedding. scripts/ isn't a package under app/, so it's imported by adding
its directory to sys.path (no existing precedent in this repo for testing a
one-off script — this establishes the pattern)."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import backfill_context_library_embeddings as backfill


class _FakeTable:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filtered = rows
        self.updates: list[tuple[dict, str]] = []
        self._pending_eq_id: str | None = None

    def select(self, *_args, **_kwargs):
        return self

    def is_(self, key, value):
        target = None if value == "null" else value
        self._filtered = [r for r in self._rows if r.get(key) == target]
        return self

    def update(self, values: dict):
        self._pending_update = values
        return self

    def eq(self, key, value):
        if key == "id":
            self.updates.append((self._pending_update, value))
        return self

    def execute(self):
        return MagicMock(data=self._filtered)


class _FakeSupabase:
    def __init__(self, rows: list[dict]):
        self._table = _FakeTable(rows)

    def table(self, _name: str):
        return self._table


@pytest.mark.asyncio
async def test_backfill_only_updates_rows_missing_embedding():
    rows = [
        {"id": "row-1", "title": "Needs embedding", "body": "...", "embedding": None},
        {"id": "row-2", "title": "Already embedded", "body": "...", "embedding": [0.1] * 768},
    ]
    fake_supabase = _FakeSupabase(rows)
    fake_embedding = [0.9] * 768

    with (
        patch.object(backfill, "get_supabase", return_value=fake_supabase),
        patch.object(backfill, "embed_document_content", new=AsyncMock(return_value=fake_embedding)),
    ):
        await backfill.main()

    assert len(fake_supabase._table.updates) == 1
    updated_payload, updated_id = fake_supabase._table.updates[0]
    assert updated_id == "row-1"
    assert updated_payload == {"embedding": fake_embedding}


@pytest.mark.asyncio
async def test_backfill_is_a_noop_when_nothing_needs_it():
    fake_supabase = _FakeSupabase([{"id": "row-1", "title": "t", "body": "b", "embedding": [0.1] * 768}])

    with (
        patch.object(backfill, "get_supabase", return_value=fake_supabase),
        patch.object(backfill, "embed_document_content", new=AsyncMock()) as fake_embed,
    ):
        await backfill.main()

    fake_embed.assert_not_called()
