from enum import Enum
from uuid import UUID

from pydantic import Field

from app.models.base import CamelModel


class UserRole(str, Enum):
    ADMIN = "admin"
    GENERAL = "general"


class User(CamelModel):
    id: UUID
    email: str
    role: UserRole
    assigned_client_ids: list[UUID] = Field(default_factory=list)
