from enum import Enum
from uuid import UUID

from pydantic import Field

from app.models.base import CamelModel


class UserRole(str, Enum):
    ADMIN = "admin"
    GENERAL = "general"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(CamelModel):
    id: UUID
    email: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    assigned_client_ids: list[UUID] = Field(default_factory=list)


class UserCreate(CamelModel):
    email: str
    role: UserRole


class PasswordResetRequest(CamelModel):
    email: str
