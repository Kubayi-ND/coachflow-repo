from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.ai.icf_rubric import COMPETENCIES, RUBRIC_VERSION
from app.models.base import CamelModel

IcfRating = Literal["not_observed", "emerging", "meets_pcc", "exceeds_pcc"]


class Scorecard(CamelModel):
    id: UUID
    session_id: UUID
    structured_critique: dict[str, Any]
    citations: list[dict[str, Any]] = Field(default_factory=list)


# --- Post-session ICF critique ---------------------------------------------
# The exact shape the post-session prompt asks Gemini for. Validated before
# anything is stored (services/post_session.py), then saved as
# scorecards.structured_critique with snake_case keys the frontend reads.


class Evidence(BaseModel):
    quote: str
    line: int | None = None  # the transcript's L<n> line number
    speaker: str | None = None
    verified: bool = True  # set by post_session: False if the quote isn't in the transcript


class MarkerObservation(BaseModel):
    id: str  # PCC marker id, e.g. "7.6"
    observed: bool
    note: str = ""


class CompetencyAssessment(BaseModel):
    id: int = Field(ge=1, le=8)
    name: str
    rating: IcfRating
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    pcc_markers: list[MarkerObservation] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    growth_areas: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)  # Context Library row ids


class OverallAlignment(BaseModel):
    rating: IcfRating
    summary: str


class IcfCritique(BaseModel):
    rubric_version: str = RUBRIC_VERSION
    overall_alignment: OverallAlignment
    competencies: list[CompetencyAssessment]
    top_strengths: list[str] = Field(default_factory=list)
    top_growth_areas: list[str] = Field(default_factory=list)
    coach_action_items: list[str] = Field(default_factory=list)
    client_action_items: list[str] = Field(default_factory=list)
    talk_ratio_estimate: str | None = None
    transcript_unverified: bool = False  # set by post_session for partial parses

    @field_validator("competencies")
    @classmethod
    def _all_eight_competencies_once(cls, value: list[CompetencyAssessment]) -> list[CompetencyAssessment]:
        expected = {competency.id for competency in COMPETENCIES}
        ids = [assessment.id for assessment in value]
        if sorted(ids) != sorted(expected):
            raise ValueError(f"expected one assessment per ICF competency {sorted(expected)}, got {ids}")
        return sorted(value, key=lambda assessment: assessment.id)


class PostSessionOutput(BaseModel):
    scorecard: IcfCritique
    client_summary: str = Field(min_length=1)
