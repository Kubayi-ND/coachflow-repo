"""Prompt for the annual_review session type (pre-session prep + post-session artifacts).
annual_review context must only draw on prior annual_review sessions, per
backend/CLAUDE.md phase 4.
"""

PRE_TEMPLATE = """\
You are preparing a coach for an upcoming Annual Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Annual Strategic Reviews with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing year-over-year progress and 2-3 focus areas
for this review. Ground every claim in the material above.
"""

POST_TEMPLATE = """\
You are producing the post-session artifacts for an Annual Strategic Review
that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
"""
