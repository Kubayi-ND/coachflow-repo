# AUTO-GENERATED from shared/types/session-types.json. Do not edit by hand.
# Regenerate: python shared/types/scripts/generate_session_types.py

from enum import Enum
from typing import NamedTuple


class SessionType(str, Enum):
    ONE_ON_ONE = "one_on_one"
    QUARTERLY_REVIEW = "quarterly_review"
    ANNUAL_REVIEW = "annual_review"
    MONTHLY_COUNCIL = "monthly_council"


class SessionTypeDefinition(NamedTuple):
    id: SessionType
    label: str
    naming_pattern: str
    lead_time_working_days: int


SESSION_TYPES: dict[SessionType, SessionTypeDefinition] = {
    SessionType.ONE_ON_ONE: SessionTypeDefinition(SessionType.ONE_ON_ONE, '1-on-1 Executive Coaching', 'Grow Executive Coaching [Coachee Name]', 3),
    SessionType.QUARTERLY_REVIEW: SessionTypeDefinition(SessionType.QUARTERLY_REVIEW, 'Quarterly Strategic Review', 'Grow Quarterly Strategic Review', 5),
    SessionType.ANNUAL_REVIEW: SessionTypeDefinition(SessionType.ANNUAL_REVIEW, 'Annual Strategic Review', 'Grow Annual Strategic Review', 10),
    SessionType.MONTHLY_COUNCIL: SessionTypeDefinition(SessionType.MONTHLY_COUNCIL, 'Monthly Strategic Council', 'Grow Monthly Strategic Council', 5),
}
