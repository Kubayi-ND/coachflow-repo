"""Prompt for the quarterly_review session type (pre-session prep + post-session artifacts).
quarterly_review context must only draw on prior quarterly_review sessions — never
1-on-1 or annual-review history, per backend/CLAUDE.md phase 4.
"""

PRE_TEMPLATE = """\
You are preparing a coach for an upcoming Quarterly Strategic Review.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Quarterly Strategic Reviews with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing quarter-over-quarter progress against prior
strategic goals and 2-3 focus areas for this review. Ground every claim in
the material above.
"""

POST_TEMPLATE = """\
You are producing the post-session artifacts for a Quarterly Strategic Review
that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
"""
