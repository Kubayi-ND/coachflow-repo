from uuid import UUID

from app.models.base import CamelModel


class ContextLibraryEntry(CamelModel):
    id: UUID
    entry_group_id: UUID
    client_id: UUID | None = None  # null = org-wide (ICF/GROW docs)
    title: str  # required heading describing what this entry covers
    body: str
    version: int
    created_at: str


class ContextLibraryEntryCreate(CamelModel):
    client_id: UUID | None = None
    title: str
    body: str


class ContextLibraryEntryVersion(CamelModel):
    title: str
    body: str
