from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.base import CamelModel


class Scorecard(CamelModel):
    id: UUID
    session_id: UUID
    structured_critique: dict[str, Any]
    citations: list[dict[str, Any]] = Field(default_factory=list)
