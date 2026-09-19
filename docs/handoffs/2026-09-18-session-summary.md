# Session summary — 2026-09-18

A summary of one working session on CoachFlow: what was asked, what was done, where things stand, and what's still needed. For the technical detail (file-by-file changes, the RAG gap list, the roadmap), see [`2026-09-18-privacy-lockdown-and-rag-audit.md`](2026-09-18-privacy-lockdown-and-rag-audit.md) in this folder.

## Quick status

| | |
|---|---|
| Branch | `luyanda/privacy-lockdown`, pushed to `origin` and merged with `origin/main` as of PR #5 |
| Pull request | **Not opened yet**: `gh` isn't installed on this machine. Open it at https://github.com/Kubayi-ND/coachflow-repo/compare/main...luyanda/privacy-lockdown?expand=1 |
| Tests | As of 2026-09-19: backend ruff, mypy and pytest pass (98 tests); frontend typecheck, lint (one existing warning in `Toast.tsx`) and vitest (11 tests) pass. |
| Live database | **Not changed yet.** Both patches (2026-09-18 lockdown, then 2026-09-19 ICF critique and prompt descriptions) still have to be run against the live Supabase project. |
| Design canvas | https://claude.ai/artifact/QYHvrFAFx8EurStrGtP3Ar (it predates the lockdown code) |

## What was asked, in order

1. **Document the changes on the branch.** This became a design canvas.
2. **Focus it on schema and siloing, and don't cite the spec** (`docs/grow-hackathon-case-study.md` is outdated). The canvas was rebuilt around this.
3. **Treat the tenant concern as outdated.** Instead: work out how to address privacy and leakage, check whether the system really is RAG, and say how to optimise it. This produced an audit, a plan, and then the privacy lockdown.
4. **Sum up the session so the work carries into another one.** This produced a commit, merge, push, a handoff doc and memory notes.

## 1. Branch documentation (design canvas)

The branch `luyanda/ui-redesign` held three earlier commits: docs aligned to decisions D-01 to D-09, a requirements-traceability table, and small lint and CI fixes. None of them changed the schema or retrieval code; they documented the rules.

The canvas has four boards comparing `main` with the branch's design:
- **Overview:** the boundaries that keep information apart.
- **Schema, today vs planned:** the planned tables, and which tables have row-level security.
- **What a session can see:** diagrams of today's retrieval vs the engagement model.
- **Individual → team sharing:** the only allowed path across the silo.

## 2. Is it RAG? Partly

**Yes, but only in one path.** Pre-session prep (`GET /sessions/{id}/prep` and the hourly reminder job) does real retrieval-augmented generation:
1. It embeds a query with Gemini `gemini-embedding-2` (768 dimensions).
2. It runs a pgvector cosine top-6 search over the client's own Context Library entries.
3. It puts the results into the prompt template and calls Gemini.

Where it falls short:
- **The post-session scorecard path never runs.** Nothing calls it, and transcripts aren't linked to sessions.
- **Past-session history is always empty.** Nothing sets `sessions.status = 'sent'`.
- **Org-wide documents are pasted into every prompt whole** instead of being searched.
- **No chunking.** A whole PDF is one vector.
- **The vector index is never used.** The search runs through a view the index can't serve.
- **Weak retrieval and grounding.** There's no relevance threshold, no hybrid search, no reranking, no citation checks, no token budget and no evaluation set.

**Agreed order for the RAG work** (not started):
1. Make the loop run.
2. Chunking.
3. Rank org-wide documents too.
4. Hybrid search.
5. Better queries.
6. Grounding and citations.
7. Index use and caching.
8. An evaluation set.

## 3. Privacy and leakage audit: what was found

- **The database was open.** Anyone holding the public anon key (it ships in the frontend) could read transcripts, drafts, scorecards and client rows directly, because only two tables had row-level security. The `match_context_library` function returned any client's notes to anyone.
- **The API barely checked access.** Only 3 routes checked whether a coach was assigned to the client. Any coach could read, edit and **send** another client's draft, read any scorecard, and read or overwrite any client's Context Library notes.
- **Sessions could be attributed to the wrong person.** Import code attached events to "the first matching attendee", so a team session could land on an individual. The live calendar scanner was broken: it wrote sessions with no client.
- **Personal documents were org-wide.** A personal psychometric report was imported as org-wide, so it went into every client's prompt.
- **Gemini was called on every view.** Prep was regenerated each time a session was opened, and there was no guidance on the paid-tier key.

## 4. Privacy lockdown: what was built

**Database** (`backend/app/db/schema.sql`, plus the idempotent patch `backend/app/db/patches/2026-09-18_privacy_lockdown.sql` for existing databases):
- Row-level security on every table, with no access for the anon or signed-in roles (except each coach's own reminder rules).
- Table grants and the `match_context_library` grant revoked; the `_current` views run with the caller's permissions.
- New: `sessions.external_event_id`, `transcripts.session_id`, a unique key on `unmatched_events`, and a `coach_briefings` table.

**API** (helpers in `backend/app/core/security.py`):
- Drafts, scorecards, sessions, prep and the Context Library routes check the coach's assigned clients.
- Approving a draft always sends to the session's own client.
- Only admins can create or edit org-wide Context Library entries, or change a client's email address.

**AI context:**
- One scope function, `resolve_retrieval_scope` in `context_builder.py`, checks every row before it can reach a prompt.

**Attribution:**
- Matching needs exactly one client. Only 1-on-1s are matched automatically; quarterly, annual and monthly events go to the unmatched queue.
- The live calendar scanner is fixed and saves sessions by calendar event id.
- Transcripts only link to a session within 2 days of it.

**Gemini:**
- Prep is saved and re-served; `?refresh=true` regenerates it.
- The docs say the key must be on the paid tier.

**Hardening:**
- CORS limited to `CORS_ALLOWED_ORIGINS` (it was `*`).
- Constant-time webhook secret check.
- The login token's audience and issuer are verified.
- Fixed a bug already on `main` where `create_client` was shadowed in `repository.py`.

**Frontend:**
- Logout clears cached data.
- New Context Library entries default to a client; only admins see the org-wide option.

**Tests:**
- New `backend/tests/test_access_control.py` covers each route.
- New tests for matching, the retrieval scope, the calendar scanner and the backfill.

**Behaviour changes to know about:**
- Quarterly, annual and monthly calendar events no longer attach to a client automatically.
- Approving a draft returns 409 if the client has no email; it used to send to an empty address.

## 5. Packaging and handoff

- **Commits on `luyanda/privacy-lockdown`:** the lockdown, a merge of `origin/main` (the only conflict was the `create_client` import line, which upstream had fixed the same way), and the docs.
- **Docs updated:**
  - [`2026-09-18-privacy-lockdown-and-rag-audit.md`](2026-09-18-privacy-lockdown-and-rag-audit.md): the full technical handoff.
  - `docs/requirements-traceability.md`: the confidentiality, individual/team silo and briefing rows move from Conflict to Partial.
  - `MIGRATION.md`: the new env var, the paid-tier Gemini key, the database patch step, and a check that the anon key can't read data.
  - `backend/CLAUDE.md`: the authorization pattern and database layer.
- **Claude memory:** new notes on the lockdown status, RAG status and "spec is outdated"; the individual/team silo and local-environment notes are updated.

## 6. Still needed

1. **Open the PR** at the link in Quick status.
2. **Run the database patch on the live Supabase project.** Until then the database is still open to the anon key.
   1. Run the grants check in the patch header.
   2. Run `psql "$DATABASE_URL" -f backend/app/db/patches/2026-09-18_privacy_lockdown.sql`.
   3. Confirm `curl "$SUPABASE_URL/rest/v1/clients?select=*" -H "apikey: $ANON_KEY"` returns an error or `[]`.
   4. Then run `backend/app/db/patches/2026-09-19_icf_critique_and_prompt_descriptions.sql` (see section 8), and re-import the ICF Context Library file if it was imported before 2026-09-19.
3. **Set the environment:** `CORS_ALLOWED_ORIGINS` to the deployed frontend, and confirm `GEMINI_API_KEY` is on the paid tier.
4. **Decide on the org-wide documents** `iEQ9 Joss du Trevou CC.pdf` and `Joss du Trevou Coach Profile .pdf`. They go into every client's prompt. They're probably the coach's own documents, but that should be a deliberate choice. Also review anything else org-wide (`select title from context_library_current where client_id is null;`).
5. **Known gap:** unmatched calendar events are still visible to every coach, because they have no client.

## 7. What's next

1. **The individual/team engagement model:** companies, individual vs team clients, and acknowledged, revocable sharing from an individual into a team. It plugs into `resolve_retrieval_scope`.
2. **The RAG work,** in the order listed in section 2.
3. **Supabase CLI migrations** (D-09). The baseline must include this lockdown.

## 8. Follow-up session — 2026-09-19

Asked for: a post-session analysis and critique grounded in ICF material, so the coach knows where to improve and whether they're aligned with ICF standards; a description for each prompt in the prompt library; and my pick of quality-of-life features from the R&D prototype.

Built (details in the technical handoff, section 5):
- **ICF post-session critique.** After a session, the coach's coaching is rated against the 8 ICF core competencies and 37 PCC markers. Each rating comes with word-for-word transcript quotes, PCC markers observed or missed, strengths, where to improve, and what to practise next session. Only the coach sees it.
  - It runs automatically when a transcript is linked to a session, or from an **Analyse session** button.
  - The client summary from the same run waits in Approvals.
  - Citations and quotes are checked, so anything unsupported is dropped or flagged.
  - Real Gemini and Plaud transcript exports now parse; they used to fail.
- **Prompt descriptions.** Each prompt says when it runs, what it uses, and what it produces. There's also a Copy prompt button.
- **Quality of life from the R&D prototype:**
  - client search and filters;
  - sessions grouped by day, with times;
  - a clickable Need attention tile;
  - copy buttons on prep;
  - a confidential line in the session panel;
  - dismissible toasts;
  - better empty states.

  Skipped, with reasons in the handoff: commitments tracking, the fake sync indicator, caching client data in the browser, free-form prompts, and the 5-part prep.

Tests: backend 98 pass, frontend 11 pass. New database patch: `backend/app/db/patches/2026-09-19_icf_critique_and_prompt_descriptions.sql`.

