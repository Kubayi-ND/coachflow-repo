"""Pre-session prep prompt for the one_on_one session type."""

TEMPLATE = """\
You are preparing a coach for an upcoming 1-on-1 executive coaching session.

## Client profile
{client_profile}

## Context Library (ICF competencies + GROW model, relevant slice)
{context_library}

## Prior 1-on-1 sessions with this client (most recent first)
{prior_sessions}

Draft a prep email to the coach summarizing: open threads from the last
session, suggested GROW-model focus areas for this session, and 2-3 questions
worth raising. Ground every claim in the Context Library or prior-session
material above — do not invent history. Write in plain prose, ready to send
after coach review.
"""
