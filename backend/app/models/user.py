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
    must_reset_password: bool = False
    assigned_client_ids: list[UUID] = Field(default_factory=list)


class UserCreate(CamelModel):
    email: str
    role: UserRole


class UserCreateResult(CamelModel):
    """Response for admin user creation: the temporary password is only ever
    returned here, once — it isn't stored anywhere and can't be retrieved
    again, so the admin must copy it to hand to the coach out of band."""

    user: User
    temporary_password: str


class PasswordResetRequest(CamelModel):
    email: str
