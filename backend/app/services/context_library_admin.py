"""Context Library writes with embedding computation — the counterpart to
user_admin.py's Auth-provisioning pattern. admin.py's context-library routes
call through here rather than app.db.repository's insert functions directly,
so repository.py stays a pure data-access layer with no app.ai imports.
"""
from typing import Any
from uuid import UUID

from app.ai.embeddings import embed_document_content
from app.db.repository import create_context_library_entry, post_context_library_version


async def create_context_library_entry_with_embedding(client_id: UUID | None, title: str, body: str) -> dict[str, Any]:
    embedding = await embed_document_content(title, body)
    return await create_context_library_entry(client_id, title, body, embedding=embedding)


async def post_context_library_version_with_embedding(entry_group_id: UUID, title: str, body: str) -> dict[str, Any]:
    embedding = await embed_document_content(title, body)
    return await post_context_library_version(entry_group_id, title, body, embedding=embedding)
