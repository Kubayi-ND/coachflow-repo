from uuid import UUID

from pydantic import Field

from app.models.base import CamelModel
from app.session_types_generated import SessionType


class Client(CamelModel):
    id: UUID
    name: str
    email: str
    coach_user_id: UUID
    tenant_id: str
    drive_folder_id: str | None = None
    session_types: list[SessionType] = Field(default_factory=list)


class ClientCreate(CamelModel):
    """coach_user_id is intentionally absent — a client is always self-assigned
    to the authenticated coach creating it, never caller-supplied. `context`
    is request-only (not a `clients` column): if present, the route seeds it
    as a client-scoped Context Library entry instead."""

    name: str
    email: str
    tenant_id: str
    drive_folder_id: str | None = None
    session_types: list[SessionType] = Field(default_factory=list)
    context: str | None = None


class ClientUpdate(CamelModel):
    name: str | None = None
    email: str | None = None
    tenant_id: str | None = None
    drive_folder_id: str | None = None
    session_types: list[SessionType] | None = None
