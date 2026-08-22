"""Unit tests for the one-time local-file backfill (services/local_backfill.py).
Mocks every Supabase call — CI must never make a live call (backend/CLAUDE.md
testing notes).
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.client import Client as ClientModel
from app.models.imports import ImportItemStatus, ImportSource
from app.services import local_backfill


def _client(name: str, email: str = "client@example.com") -> ClientModel:
    return ClientModel(
        id=uuid4(),
        name=name,
        email=email,
        coach_user_id=uuid4(),
        tenant_id="tenant_a",
        drive_folder_id=None,
        session_types=[],
    )


def test_parse_frontmatter_splits_block_and_body():
    raw = "---\nclient: Jane Doe\ntitle: Notes\n---\nBody line one.\nBody line two.\n"
    frontmatter, body = local_backfill._parse_frontmatter(raw)
    assert frontmatter == {"client": "Jane Doe", "title": "Notes"}
    assert body == "Body line one.\nBody line two."


def test_parse_frontmatter_returns_empty_when_no_block():
    frontmatter, body = local_backfill._parse_frontmatter("Just a plain file.\n")
    assert frontmatter == {}
    assert body == "Just a plain file.\n"


def test_as_aware_iso_adds_midnight_utc_to_bare_date():
    assert local_backfill._as_aware_iso("2026-01-10") == "2026-01-10T00:00:00+00:00"
    assert local_backfill._as_aware_iso("2026-01-10T08:00:00+00:00") == "2026-01-10T08:00:00+00:00"


@pytest.mark.asyncio
async def test_missing_category_directory_reports_zero_without_any_supabase_call():
    with patch("app.services.local_backfill.get_supabase") as mock_get_supabase:
        counts = await local_backfill.import_local_calendar("tenant_a", Path("/does/not/exist"), Path("/does/not"), dry_run=False)

    assert counts == {"total": 0, "succeeded": 0, "failed": 0, "unmatched": 0}
    mock_get_supabase.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_client_notes_makes_no_writes(tmp_path):
    notes_dir = tmp_path / "client-notes"
    notes_dir.mkdir()
    (notes_dir / "jane.md").write_text("---\nclient: Jane Doe\n---\nSome notes.\n", encoding="utf-8")

    with (
        patch("app.services.local_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[_client("Jane Doe")])),
        patch("app.services.local_backfill.create_import_job", new=AsyncMock()) as fake_create_job,
        patch("app.services.local_backfill.record_import_item", new=AsyncMock()) as fake_record,
        patch("app.services.local_backfill.create_context_library_entry_with_embedding", new=AsyncMock()) as fake_create_entry,
    ):
        counts = await local_backfill.import_local_client_notes("tenant_a", notes_dir, tmp_path, dry_run=True)

    assert counts == {"total": 1, "succeeded": 1, "failed": 0, "unmatched": 0}
    fake_create_job.assert_not_called()
    fake_record.assert_not_called()
    fake_create_entry.assert_not_called()


@pytest.mark.asyncio
async def test_uploaded_grow_context_library_imports_text_only(tmp_path):
    context_dir = tmp_path / "Grow Context Library"
    context_dir.mkdir()
    context_file = context_dir / "ICF CCs with PCC Markers 0326 PLAIN TEXT.txt"
    context_file.write_text("ICF competency guidance.", encoding="utf-8")
    (context_dir / "Coaching Preparation Prompt.docx").write_bytes(b"prompt document")

    with patch("app.services.local_backfill.import_local_context_library", new=AsyncMock(return_value={
        "total": 1, "succeeded": 1, "failed": 0, "unmatched": 0
    })) as fake_import:
        await local_backfill.run_local_backfill(
            "tenant_a", tmp_path, sources={ImportSource.CONTEXT_LIBRARY}, dry_run=True
        )

    fake_import.assert_awaited_once_with("tenant_a", context_dir, tmp_path, dry_run=True)


@pytest.mark.asyncio
async def test_client_notes_matches_frontmatter_and_dedups_on_rerun(tmp_path):
    notes_dir = tmp_path / "client-notes"
    notes_dir.mkdir()
    (notes_dir / "jane.md").write_text("---\nclient: Jane Doe\ntitle: Session notes\n---\nSome notes.\n", encoding="utf-8")
    matched_client = _client("Jane Doe")

    with (
        patch("app.services.local_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[matched_client])),
        patch("app.services.local_backfill.create_import_job", new=AsyncMock(return_value={"id": str(uuid4())})),
        patch("app.services.local_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.local_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.local_backfill.record_import_item", new=AsyncMock()) as fake_record,
        patch("app.services.local_backfill.create_context_library_entry_with_embedding", new=AsyncMock()) as fake_create_entry,
    ):
        counts = await local_backfill.import_local_client_notes("tenant_a", notes_dir, tmp_path, dry_run=False)

    assert counts == {"total": 1, "succeeded": 1, "failed": 0, "unmatched": 0}
    fake_create_entry.assert_awaited_once_with(matched_client.id, "Session notes", "Some notes.")
    assert fake_record.call_args.args[6] == ImportItemStatus.IMPORTED

    # Re-run: get_import_item_by_file now reports it already imported — should skip re-inserting.
    with (
        patch("app.services.local_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[matched_client])),
        patch("app.services.local_backfill.create_import_job", new=AsyncMock(return_value={"id": str(uuid4())})),
        patch("app.services.local_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.local_backfill.get_import_item_by_file", new=AsyncMock(return_value={"status": "imported"})),
        patch("app.services.local_backfill.record_import_item", new=AsyncMock()) as fake_record_rerun,
        patch("app.services.local_backfill.create_context_library_entry_with_embedding", new=AsyncMock()) as fake_create_entry_rerun,
    ):
        counts_rerun = await local_backfill.import_local_client_notes("tenant_a", notes_dir, tmp_path, dry_run=False)

    assert counts_rerun == {"total": 1, "succeeded": 1, "failed": 0, "unmatched": 0}
    fake_create_entry_rerun.assert_not_awaited()
    fake_record_rerun.assert_not_called()


@pytest.mark.asyncio
async def test_client_notes_unmatched_when_no_frontmatter_client(tmp_path):
    notes_dir = tmp_path / "client-notes"
    notes_dir.mkdir()
    (notes_dir / "mystery.md").write_text("No frontmatter here at all.\n", encoding="utf-8")

    with (
        patch("app.services.local_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[])),
        patch("app.services.local_backfill.create_import_job", new=AsyncMock(return_value={"id": str(uuid4())})),
        patch("app.services.local_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.local_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.local_backfill.record_import_item", new=AsyncMock()) as fake_record,
        patch("app.services.local_backfill.create_context_library_entry_with_embedding", new=AsyncMock()) as fake_create_entry,
    ):
        counts = await local_backfill.import_local_client_notes("tenant_a", notes_dir, tmp_path, dry_run=False)

    assert counts == {"total": 1, "succeeded": 0, "failed": 0, "unmatched": 1}
    fake_create_entry.assert_not_awaited()
    assert fake_record.call_args.args[6] == ImportItemStatus.UNMATCHED_CLIENT


@pytest.mark.asyncio
async def test_import_local_transcripts_strips_frontmatter_before_insert(tmp_path):
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    (transcripts_dir / "jane.md").write_text(
        "---\nclient: Jane Doe\ndate: 2026-01-10\n---\nCoach: How are you?\nJane: Doing well.\n", encoding="utf-8"
    )
    matched_client = _client("Jane Doe")

    with (
        patch("app.services.local_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[matched_client])),
        patch("app.services.local_backfill.create_import_job", new=AsyncMock(return_value={"id": str(uuid4())})),
        patch("app.services.local_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.local_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.local_backfill.record_import_item", new=AsyncMock()),
        patch("app.services.local_backfill.insert_transcript_and_link", new=AsyncMock()) as fake_insert,
    ):
        counts = await local_backfill.import_local_transcripts("tenant_a", transcripts_dir, tmp_path, dry_run=False)

    assert counts == {"total": 1, "succeeded": 1, "failed": 0, "unmatched": 0}
    fake_insert.assert_awaited_once()
    call_args = fake_insert.call_args.args
    assert call_args[0] is matched_client
    raw_bytes = call_args[3]
    assert b"client: Jane Doe" not in raw_bytes  # frontmatter must be stripped before normalize() sees it
    assert b"Coach: How are you?" in raw_bytes
    assert call_args[4] == "2026-01-10T00:00:00+00:00"
