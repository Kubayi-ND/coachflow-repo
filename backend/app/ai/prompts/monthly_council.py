"""Prompt for the monthly_council session type (pre-session prep + post-session artifacts).
monthly_council context must only draw on prior monthly_council sessions, per
backend/CLAUDE.md phase 4.
"""

PRE_TEMPLATE = """\
You are preparing a coach for an upcoming Monthly Strategic Council session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior Monthly Strategic Council sessions with this client (most recent first)
{prior_sessions}

Draft a prep email summarizing open action items and 2-3 focus areas for this
council session. Ground every claim in the material above.
"""

POST_TEMPLATE = """\
You are producing the post-session artifacts for a Monthly Strategic Council
session that just occurred.

## Transcript (normalized)
{transcript}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Client profile
{client_profile}

Respond with JSON only: {{"scorecard": {{...with "citations"...}}, "client_summary": "..."}}.
"""
