"""app/services/context_library_admin.py — asserts the computed embedding
flows into the repository insert call."""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services import context_library_admin


@pytest.mark.asyncio
async def test_create_entry_with_embedding_passes_embedding_through():
    client_id = uuid4()
    fake_embedding = [0.1] * 768
    fake_create = AsyncMock(return_value={"id": "row-1", "client_id": str(client_id), "title": "t", "body": "b", "version": 1})

    with (
        patch.object(context_library_admin, "embed_document_content", new=AsyncMock(return_value=fake_embedding)),
        patch.object(context_library_admin, "create_context_library_entry", new=fake_create),
    ):
        row = await context_library_admin.create_context_library_entry_with_embedding(client_id, "t", "b")

    fake_create.assert_called_once_with(client_id, "t", "b", embedding=fake_embedding)
    assert row["id"] == "row-1"


@pytest.mark.asyncio
async def test_post_version_with_embedding_passes_embedding_through():
    entry_group_id = uuid4()
    fake_embedding = [0.2] * 768
    fake_post = AsyncMock(return_value={"id": "row-2", "entry_group_id": str(entry_group_id), "title": "t2", "body": "b2", "version": 2})

    with (
        patch.object(context_library_admin, "embed_document_content", new=AsyncMock(return_value=fake_embedding)),
        patch.object(context_library_admin, "post_context_library_version", new=fake_post),
    ):
        row = await context_library_admin.post_context_library_version_with_embedding(entry_group_id, "t2", "b2")

    fake_post.assert_called_once_with(entry_group_id, "t2", "b2", embedding=fake_embedding)
    assert row["id"] == "row-2"


@pytest.mark.asyncio
async def test_prompt_template_version_carries_description_over_when_omitted():
    from unittest.mock import MagicMock

    from app.db import repository

    current = {
        "id": "t1", "entry_group_id": "g1", "session_type": "one_on_one", "phase": "post",
        "title": "Old", "description": "What this prompt does", "body": "old", "version": 2,
    }
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        current
    ]
    supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "t2"}]

    with patch.object(repository, "get_supabase", return_value=supabase):
        await repository.post_prompt_template_version(uuid4(), "New", "new body")
        inserted = supabase.table.return_value.insert.call_args.args[0]
        assert inserted["description"] == "What this prompt does"
        assert inserted["version"] == 3

        await repository.post_prompt_template_version(uuid4(), "New", "new body", description="Updated")
        assert supabase.table.return_value.insert.call_args.args[0]["description"] == "Updated"
