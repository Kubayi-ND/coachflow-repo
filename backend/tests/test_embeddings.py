"""app/ai/embeddings.py — mocks the Gemini SDK call directly, CI must never
make a live call (backend/CLAUDE.md testing notes)."""
from unittest.mock import AsyncMock, patch

import pytest

from app.ai import embeddings


@pytest.mark.asyncio
async def test_embed_document_content_uses_retrieval_document_task_type():
    fake_embed = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
    with patch.object(embeddings.genai, "embed_content_async", new=fake_embed):
        result = await embeddings.embed_document_content("ICF Competency 3", "Establishing trust.")

    assert result == [0.1, 0.2, 0.3]
    fake_embed.assert_called_once_with(
        model="models/gemini-embedding-2",
        content="ICF Competency 3\n\nEstablishing trust.",
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768,
        title="ICF Competency 3",
    )


@pytest.mark.asyncio
async def test_embed_query_text_uses_retrieval_query_task_type_with_no_title():
    fake_embed = AsyncMock(return_value={"embedding": [0.4, 0.5, 0.6]})
    with patch.object(embeddings.genai, "embed_content_async", new=fake_embed):
        result = await embeddings.embed_query_text("Upcoming 1-on-1 session for Jane Doe.")

    assert result == [0.4, 0.5, 0.6]
    fake_embed.assert_called_once_with(
        model="models/gemini-embedding-2",
        content="Upcoming 1-on-1 session for Jane Doe.",
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768,
    )
