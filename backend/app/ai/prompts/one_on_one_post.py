"""Post-session scorecard + summary prompt for the one_on_one session type."""

TEMPLATE = """\
You are producing the post-session artifacts for a 1-on-1 executive coaching
session that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Produce a JSON object with two top-level keys:
- "scorecard": a structured ICF/GROW critique of the coach's performance in
  this session, with a "citations" array linking each claim back to the
  specific Context Library section id it was grounded in. This is internal
  only — do not soften findings for a client audience.
- "client_summary": a plain-prose session summary suitable for the
  client-facing draft, focused on their stated goals and next steps only —
  no internal critique content.

Respond with JSON only, matching this shape exactly.
"""
