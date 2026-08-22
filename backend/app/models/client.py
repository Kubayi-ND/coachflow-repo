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
    name: str
    email: str
    coach_user_id: UUID
    tenant_id: str
    drive_folder_id: str | None = None
    session_types: list[SessionType] = Field(default_factory=list)
