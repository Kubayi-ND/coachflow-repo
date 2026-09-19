"""Unit tests for the one-time Drive backfill (services/drive_backfill.py).
Mocks every Drive/Supabase call — CI must never make a live call to either
(backend/CLAUDE.md testing notes).
"""
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.client import Client as ClientModel
from app.models.imports import ImportItemStatus, ImportSource
from app.services import drive_backfill


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


def test_parse_calendar_events_accepts_list_items_wrapper_and_bare_event():
    assert drive_backfill.parse_calendar_events(b'[{"summary": "a"}]') == [{"summary": "a"}]
    assert drive_backfill.parse_calendar_events(b'{"items": [{"summary": "a"}]}') == [{"summary": "a"}]
    assert drive_backfill.parse_calendar_events(b'{"summary": "a"}') == [{"summary": "a"}]


@pytest.mark.asyncio
async def test_import_per_client_folder_matches_and_flags_unmatched_subfolder():
    matched_client = _client("Jane Doe")
    subfolders = [{"id": "folder-matched", "name": "Jane Doe"}, {"id": "folder-unmatched", "name": "Someone Else"}]
    files_by_folder = {
        "folder-matched": [{"id": "file-1", "name": "note.txt", "mimeType": "text/plain"}],
        "folder-unmatched": [{"id": "file-2", "name": "note.txt", "mimeType": "text/plain"}],
    }

    async def fake_list_folder_contents(_tenant_id, folder_id):
        return files_by_folder[folder_id]

    mock_record = AsyncMock(return_value={})

    with (
        patch("app.services.drive_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[matched_client])),
        patch("app.services.drive_backfill.list_subfolders", new=AsyncMock(return_value=subfolders)),
        patch("app.services.drive_backfill.list_folder_contents", new=fake_list_folder_contents),
        patch("app.services.drive_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.drive_backfill.record_import_item", new=mock_record),
        patch("app.services.drive_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.drive_backfill._import_one_client_note", new=AsyncMock()) as fake_import_one,
    ):
        await drive_backfill._import_per_client_folder(uuid4(), "tenant_a", "root-folder", ImportSource.CLIENT_NOTES)

    fake_import_one.assert_awaited_once()
    statuses = [call.args[6] for call in mock_record.call_args_list]
    assert ImportItemStatus.IMPORTED in statuses
    assert ImportItemStatus.UNMATCHED_CLIENT in statuses


@pytest.mark.asyncio
async def test_import_context_library_backfill_skips_already_imported_file():
    files = [{"id": "file-1", "name": "ICF Core.pdf", "mimeType": "application/pdf"}]

    with (
        patch("app.services.drive_backfill.list_folder_contents", new=AsyncMock(return_value=files)),
        patch("app.services.drive_backfill.get_import_item_by_file", new=AsyncMock(return_value={"status": "imported"})),
        patch("app.services.drive_backfill.update_import_job_progress", new=AsyncMock()),
        patch("app.services.drive_backfill.extract_text", new=AsyncMock()) as fake_extract,
        patch("app.services.drive_backfill.create_context_library_entry_with_embedding", new=AsyncMock()) as fake_create,
    ):
        await drive_backfill.import_context_library_backfill(uuid4(), "tenant_a", "folder-1")

    fake_extract.assert_not_awaited()
    fake_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_calendar_backfill_flags_matched_event_with_no_resolvable_client():
    files = [{"id": "file-1", "name": "events.json", "mimeType": "application/json"}]
    event_json = json.dumps(
        {
            "summary": "Grow Executive Coaching Jane Doe",
            "start": {"dateTime": "2026-01-05T10:00:00+00:00"},
            "attendees": [],
        }
    ).encode()

    mock_record = AsyncMock(return_value={})
    with (
        patch("app.services.drive_backfill.list_folder_contents", new=AsyncMock(return_value=files)),
        patch("app.services.drive_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.drive_backfill.download_file", new=AsyncMock(return_value=event_json)),
        patch("app.services.drive_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[])),
        patch("app.services.drive_backfill.get_supabase") as mock_get_supabase,
        patch("app.services.drive_backfill.record_import_item", new=mock_record),
        patch("app.services.drive_backfill.update_import_job_progress", new=AsyncMock()),
    ):
        mock_get_supabase.return_value.table.return_value.select.return_value.execute.return_value.data = []
        await drive_backfill.import_calendar_backfill(uuid4(), "tenant_a", "folder-1")

    assert mock_record.call_args.args[6] == ImportItemStatus.FAILED


@pytest.mark.asyncio
async def test_import_calendar_backfill_sends_team_capable_session_types_to_unmatched_queue():
    files = [{"id": "file-1", "name": "events.json", "mimeType": "application/json"}]
    event_json = json.dumps(
        {
            "summary": "Grow Quarterly Strategic Review",
            "start": {"dateTime": "2026-01-05T10:00:00+00:00"},
            "attendees": [{"email": "jane@example.com"}],
        }
    ).encode()

    mock_record = AsyncMock(return_value={})
    with (
        patch("app.services.drive_backfill.list_folder_contents", new=AsyncMock(return_value=files)),
        patch("app.services.drive_backfill.get_import_item_by_file", new=AsyncMock(return_value=None)),
        patch("app.services.drive_backfill.download_file", new=AsyncMock(return_value=event_json)),
        patch("app.services.drive_backfill.list_clients_for_tenant", new=AsyncMock(return_value=[_client("Jane Doe", "jane@example.com")])),
        patch("app.services.drive_backfill.get_supabase") as mock_get_supabase,
        patch("app.services.drive_backfill.record_import_item", new=mock_record),
        patch("app.services.drive_backfill.update_import_job_progress", new=AsyncMock()),
    ):
        mock_get_supabase.return_value.table.return_value.select.return_value.execute.return_value.data = []
        await drive_backfill.import_calendar_backfill(uuid4(), "tenant_a", "folder-1")

    # A quarterly review may be with an individual or a team (D-08): even with
    # a known client on the invite it goes to the unmatched queue, never to a
    # session attributed to that attendee.
    assert mock_record.call_args.args[6] == ImportItemStatus.IMPORTED
    tables_written = [call.args[0] for call in mock_get_supabase.return_value.table.call_args_list]
    assert "unmatched_events" in tables_written
    assert "sessions" not in tables_written


@pytest.mark.asyncio
async def test_recent_session_lookup_links_only_an_unambiguous_session():
    from unittest.mock import MagicMock

    def fake(rows):
        supabase = MagicMock()
        chain = supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value
        chain.execute.return_value.data = rows
        return supabase

    one = [{"id": str(uuid4()), "event_date": "2026-09-18T10:00:00+00:00", "transcript_id": None}]
    two = one + [{"id": str(uuid4()), "event_date": "2026-09-18T11:00:00+00:00", "transcript_id": None}]
    already_linked = [{**one[0], "transcript_id": str(uuid4())}]

    for rows, expected in ((one, one[0]["id"]), (two, None), (already_linked, None)):
        with patch("app.services.drive_backfill.get_supabase", return_value=fake(rows)):
            found = await drive_backfill.find_recent_session_for_tenant("tenant_a")
        assert (str(found) if found else None) == expected
