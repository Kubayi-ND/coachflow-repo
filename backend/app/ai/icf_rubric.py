"""The fixed ICF rubric the post-session critique scores against: the 8 ICF
Core Competencies (in their 4 domains) and the 37 PCC markers.

Marker labels here are short paraphrases for the model and the UI; the full
ICF wording lives in the org-wide Context Library entry ("ICF CCs with PCC
Markers"), which is retrieved into the same prompt and cited by id. Bump
RUBRIC_VERSION whenever this structure changes — it is stored on every
scorecard so older critiques stay interpretable.
"""
from dataclasses import dataclass

RUBRIC_VERSION = "icf-pcc-v1"

RATINGS = ("not_observed", "emerging", "meets_pcc", "exceeds_pcc")


@dataclass(frozen=True)
class Competency:
    id: int
    domain: str
    name: str
    focus: str
    markers: tuple[tuple[str, str], ...]


COMPETENCIES: tuple[Competency, ...] = (
    Competency(
        1, "Foundation", "Demonstrates Ethical Practice",
        "Integrity, respect, confidentiality, and keeping coaching distinct from consulting or therapy.",
        (),
    ),
    Competency(
        2, "Foundation", "Embodies a Coaching Mindset",
        "Open, curious, client-centred; the client owns their choices.",
        (),
    ),
    Competency(
        3, "Co-Creating the Relationship", "Establishes and Maintains Agreements",
        "Agreeing what the session is for, what success looks like, and staying on it.",
        (
            ("3.1", "Identifies or reconfirms what the client wants from this session"),
            ("3.2", "Defines or reconfirms how success will be measured"),
            ("3.3", "Explores why this matters to the client"),
            ("3.4", "Defines what the client needs to address to get there"),
        ),
    ),
    Competency(
        4, "Co-Creating the Relationship", "Cultivates Trust and Safety",
        "A safe space where the client can share freely.",
        (
            ("4.1", "Acknowledges the client's talents, insights and work"),
            ("4.2", "Shows support, empathy and concern"),
            ("4.3", "Supports the client expressing feelings, beliefs and concerns"),
            ("4.4", "Invites the client to respond to the coach's contributions and accepts the response"),
        ),
    ),
    Competency(
        5, "Co-Creating the Relationship", "Maintains Presence",
        "Fully present, flexible and grounded; comfortable with not knowing and with silence.",
        (
            ("5.1", "Responds to the whole person (the who)"),
            ("5.2", "Responds to what the client wants from the session (the what)"),
            ("5.3", "Lets the client choose what happens in the session"),
            ("5.4", "Shows curiosity to learn more about the client"),
            ("5.5", "Allows silence, pause or reflection"),
        ),
    ),
    Competency(
        6, "Communicating Effectively", "Listens Actively",
        "Hearing what is and isn't said, in the client's context.",
        (
            ("6.1", "Tailors questions and observations to who the client is"),
            ("6.2", "Explores the words the client uses"),
            ("6.3", "Explores the client's emotions"),
            ("6.4", "Explores energy shifts, non-verbal cues or other behaviours"),
            ("6.5", "Explores how the client currently sees themself or their world"),
            ("6.6", "Lets the client finish speaking without interrupting"),
            ("6.7", "Reflects or summarises succinctly for the client's clarity"),
        ),
    ),
    Competency(
        7, "Communicating Effectively", "Evokes Awareness",
        "Creating insight through powerful questions, silence, metaphor and observation.",
        (
            ("7.1", "Asks about the client's thinking, feelings, values, needs or beliefs"),
            ("7.2", "Helps the client explore new ways of seeing themself (the who)"),
            ("7.3", "Helps the client explore new ways of seeing their situation (the what)"),
            ("7.4", "Helps the client explore beyond current thinking toward their desired outcome"),
            ("7.5", "Shares observations or intuitions without attachment and invites exploration"),
            ("7.6", "Asks clear, direct, open questions one at a time, with room to think"),
            ("7.7", "Uses clear, concise language"),
            ("7.8", "Lets the client do most of the talking"),
        ),
    ),
    Competency(
        8, "Cultivating Learning and Growth", "Facilitates Client Growth",
        "Turning insight into action while supporting the client's autonomy.",
        (
            ("8.1", "Invites the client to explore progress toward the session goal"),
            ("8.2", "Invites the client to state what they learned about themself"),
            ("8.3", "Invites the client to state what they learned about their situation"),
            ("8.4", "Invites the client to consider how they will use the learning"),
            ("8.5", "Partners on post-session thinking, reflection or action"),
            ("8.6", "Partners on how to move forward: resources, support, barriers"),
            ("8.7", "Partners with the client on how they will hold themself accountable"),
            ("8.8", "Acknowledges the client's progress, learning and successes"),
            ("8.9", "Partners with the client on how to close the session"),
        ),
    ),
)

MARKER_IDS: frozenset[str] = frozenset(marker_id for c in COMPETENCIES for marker_id, _ in c.markers)


def render_rubric() -> str:
    """Rubric text for the `{icf_rubric}` prompt variable."""
    lines = [
        f"ICF rubric ({RUBRIC_VERSION}). Rate each competency: {' | '.join(RATINGS)}.",
        (
            "Competencies 1 and 2 have no PCC markers of their own: judge them from the session as a whole "
            "(ethics and confidentiality; curiosity, client ownership of choices)."
        ),
    ]
    for competency in COMPETENCIES:
        lines.append("")
        lines.append(f"{competency.id}. {competency.name} ({competency.domain}) — {competency.focus}")
        lines.extend(f"   {marker_id}: {label}" for marker_id, label in competency.markers)
    return "\n".join(lines)
