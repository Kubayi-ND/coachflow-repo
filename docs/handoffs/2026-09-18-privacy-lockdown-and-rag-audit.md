# Handoff — privacy lockdown and RAG audit (2026-09-18)

> **Updated 2026-09-19:** the post-session ICF critique, prompt descriptions and dashboard quality-of-life changes are in. See [§5](#5-update-2026-09-19-icf-critique-prompt-descriptions-quality-of-life).

Branch: `luyanda/privacy-lockdown` (includes the earlier docs-alignment commits from `luyanda/ui-redesign`, merged with `origin/main` as of PR #5).

Read this first if you're continuing this work. For the "why" behind the silo rules, see `docs/decisions.md` D-02, D-03, D-07 and D-08. Two notes on scope, from the product owner:

- **`docs/grow-hackathon-case-study.md` is out of date.** Don't cite it as the source of truth. Use `docs/decisions.md` and the `CLAUDE.md` files.
- **Tenant isolation is no longer a concern.** Privacy work is about keeping clients apart: individual vs individual, and individual vs team.

## 1. What's done (in code, tested)

Backend: ruff, mypy and 81 pytest tests all pass. Frontend: typecheck, lint and vitest all pass.

### Database: nothing is reachable with the public anon key
The browser has the Supabase anon key only for login. The backend uses the service-role key and enforces access itself. So the database denies the `anon`/`authenticated` roles everything:

- RLS on every table, with no policies except `reminder_rules`' own-row policy. The old `context_library ... using (true)` policy is dropped.
- Table and sequence grants for `anon`/`authenticated` are revoked, and so is the execute grant on `match_context_library` (it used to return any client's notes to anyone).
- `context_library_current` and `prompt_templates_current` are `security_invoker` views.
- New columns and tables:
  - `sessions.external_event_id` (unique): the calendar scanner upserts on it.
  - `transcripts.session_id`: a transcript's owner.
  - A unique key on `unmatched_events`.
  - `coach_briefings`: internal prep, never an `ai_drafts` row.

`backend/app/db/schema.sql` holds all of this for new databases. **Existing databases need `backend/app/db/patches/2026-09-18_privacy_lockdown.sql`** (idempotent). See §3.

### API: every route that exposes client data checks assigned clients
The helpers are in `backend/app/core/security.py`:
- `assert_client_access(user, client_id)`: one client.
- `assert_session_access(user, session_id)`: loads the session and checks its client. Used for drafts, scorecards and prep.
- `assert_context_library_group_access` and `assert_context_library_write_access`: Context Library history and versions. Org-wide entries are **admin-only** to create or edit, because they reach every client's prompt.
- `accessible_client_ids(user)`: pass it into the `list_*` repository functions (`None` = admin, unrestricted).

Behaviour changes:
- A coach can no longer list, approve or reject another client's drafts.
- Approve always sends to the session's own client, and returns 409 if that client has no email.
- Only admins can change `clients.email`.

`backend/tests/test_access_control.py` covers each route. **Add a case there for any new route that returns client data.**

### Retrieval: one scope function
`backend/app/services/context_builder.py`:
- `resolve_retrieval_scope(client_id)` returns a `RetrievalScope`, and `build_context` drops any row outside it. A faulty query fails closed instead of leaking.
- Company/team engagements and explicit shares plug in **here**, not in callers.
- `load_prior_sessions` was extracted, so the prep route can serve a cached briefing without calling the embedding API.

### Attribution: no more "first matching attendee"
- `backend/app/services/client_matching.py`:
  - Name and attendee-email matches require exactly one client; anything ambiguous returns `None`, and the event goes to the unmatched queue.
  - `AUTO_MATCHED_SESSION_TYPES = {one_on_one}`. Quarterly, annual and monthly events always go to the unmatched queue, because they can be with an individual or a team (D-08).
- The live `calendar_scanner.scan_tenant` was broken: it wrote sessions with no client. It now attributes 1-on-1s to one client and upserts on `external_event_id`.
- `drive_backfill` only links a transcript to a session within 2 days, and sets `transcripts.session_id`.
- `scripts/migrate_candidates_pack.py` uses the same unique-match rule; its substring token matching is gone.

### Gemini and hardening
- `GET /api/sessions/{id}/prep` serves the stored `coach_briefings` row. It only calls Gemini when there isn't one yet, or with `?refresh=true`.
- `GEMINI_API_KEY` must be a paid-tier key; this is documented in `backend/.env.example`, `backend/CLAUDE.md` and `MIGRATION.md`.
- CORS comes from `CORS_ALLOWED_ORIGINS` (it was `*`).
- The webhook secret uses a constant-time comparison.
- JWT audience (`authenticated`) and issuer (`<SUPABASE_URL>/auth/v1`) are verified.
- Fixed: `repository.create_client` shadowed supabase's `create_client` inside `get_supabase()`.

### Frontend
- `useLogout` clears the React Query cache, so the next user on the browser doesn't see the previous coach's data.
- The Context Library scope defaults to a client, and only admins see the org-wide option.

## 2. RAG status

**Verdict: yes, it's RAG, but only in one path and only partly.**

`GET /sessions/{id}/prep` and the hourly reminder job do:
1. dense retrieval: `embed_query_text`, Gemini `gemini-embedding-2`, 768 dimensions, asymmetric task types;
2. the `match_context_library` pgvector cosine top-6 over the client's own entries;
3. injection into the `prompt_templates` body;
4. `gemini_client.generate`.

Gaps, most important first:

1. ~~**The post-session path never runs.**~~ **Fixed 2026-09-19** (§5): `post_session.run_post_session_analysis` runs when a transcript is linked or on demand.
2. **Prior sessions are always empty.** Nothing sets `sessions.status='sent'`, and approving a draft doesn't update its session.
3. **Org-wide entries are stuffed in, not retrieved.** `build_context` loads every `client_id IS NULL` row whole.
4. **No chunking.** Each entry, even a whole PDF, is one vector.
5. **The HNSW index is unused.** The RPC reads the `DISTINCT ON` view.
6. **No relevance cutoff.** There's no similarity threshold, scores aren't returned, and there's no hybrid/keyword search or reranking.
7. **Weak queries.** The pre-session query is a fixed template (name + type); the post-session query is the transcript's head and tail at 4,000 characters each.
8. **No grounding checks.** Post-session output is now validated and its citations and quotes checked (§5). Still open: pre-session prep has no citations, and there's no token budget.
9. ~~**Admin templates can crash generation.**~~ **Fixed 2026-09-19:** every prompt is filled with `ai/prompt_render.render_prompt`.
10. **No retrieval evaluation.** There's no golden set, recall@k or citation-faithfulness check.

### Roadmap, in order
1. **Make the loop run:** mark sessions `held` after the event or when a transcript links, and build history per phase (D-06). (Linking transcripts and running the post-session analysis is done, §5.)
2. **Chunking:** a `context_library_chunks` table (heading/page chunks with overlap, `embedding_model` column, batched embedding).
3. **Rank org-wide reference rows too:** keep a small pinned core (ICF list, GROW summary). The RPC returns `similarity` and applies a threshold.
4. **Hybrid search:** a tsvector GIN index plus reciprocal-rank fusion.
5. **Better queries:** client goals, last summary and open action items (pre-session); a transcript summary or per-segment queries (post-session).
6. **Grounding:** `response_schema`, required citation ids validated against the retrieved set, a token budget per prompt section, safe template rendering.
7. **Performance and observability:** an `is_current` flag so HNSW is used, a query-embedding cache, `metrics_log` entries for every generation.
8. **Evaluation:** a golden set scored by recall@k and MRR in CI.

## 3. Open items / decisions needed

- **Apply the lockdown to the live Supabase project.**
  1. Run the grants query in the patch header, to see what `anon` can reach today.
  2. Run the patch.
  3. Confirm `curl "$SUPABASE_URL/rest/v1/clients?select=*" -H "apikey: $ANON_KEY"` returns an error or `[]`.
- **Review the org-wide Context Library rows** (they reach every client's prompt). Nothing was reassigned automatically. `scripts/migrate_candidates_pack.py` imported `iEQ9 Joss du Trevou CC.pdf` and `Joss du Trevou Coach Profile .pdf` as org-wide. They look like the coach's own documents, but they're personal and sent with every client. Drive and local backfills of a "context library" folder also land org-wide; list them with `select title, created_at from context_library_current where client_id is null;`.
- **Unmatched calendar events** have no client, so every coach can see their titles. This is resolved by the engagement model.
- **Next milestone (1g): the engagement model.** `companies`, `clients.kind` (individual/team) + `company_id`, and `context_shares` (acknowledged, version-pinned, revocable, and individual → individual refused server-side). Plug these into `resolve_retrieval_scope`.
- **Apply the 2026-09-19 patch too:** `backend/app/db/patches/2026-09-19_icf_critique_and_prompt_descriptions.sql`, after the lockdown patch. It adds prompt descriptions and posts the ICF post-session templates as new versions.
- **Re-import the ICF Context Library file** if it was imported before 2026-09-19. The old importer read the Mac Roman `.txt` as UTF-8, so its curly quotes and dashes are garbled (`scripts/migrate_candidates_pack.py` now decodes it correctly). Post a new version of that entry, or re-run the import for it.
- **D-09 migrations aren't set up.** Until they are, `schema.sql` plus `app/db/patches/*.sql` is the convention. When Supabase CLI migrations land, the baseline must include this lockdown.

## 4. Related artifacts
- Design canvas documenting schema and siloing, main vs this work (private to the author, shareable from its menu): https://claude.ai/artifact/QYHvrFAFx8EurStrGtP3Ar. It predates the lockdown code; §1 above is the current state.
- `docs/requirements-traceability.md`: the rows updated for this work.
- `MIGRATION.md`: env vars and post-migration checks now include the lockdown.

## 5. Update 2026-09-19: ICF critique, prompt descriptions, quality of life

### Post-session ICF critique (what the coach asked for)
After each session the coach gets a critique of **their own coaching** against the ICF Core Competencies and PCC markers, so they can see where they meet the standard and where to improve. It is coach-only: never sent, never in Approvals.

- **Rubric:** `backend/app/ai/icf_rubric.py`.
  - The 8 core competencies in their 4 domains, and the 37 PCC markers, with short paraphrased labels. The full ICF wording stays in the Context Library entry "ICF CCs with PCC Markers", which the prompt also receives.
  - Ratings are `not_observed` / `emerging` / `meets_pcc` / `exceeds_pcc`.
  - Competencies 1 and 2 have no markers, so they're judged from the session as a whole.
  - `RUBRIC_VERSION` is stored on each critique; bump it if the rubric changes.
- **What the coach sees** (frontend `features/scorecards/IcfCritique.tsx`):
  - an overall alignment rating and summary, and the talk-time estimate;
  - top strengths, where to improve, what to practise next session, and the client's commitments;
  - one card per competency: its rating, word-for-word transcript quotes with line numbers, PCC markers observed or missed, strengths and growth areas, and which Context Library entries it relied on.
- **Where it shows:**
  - the Calendar session panel's new **ICF critique** tab (with Analyse session / Analyse again);
  - the **Last review** tab, which now shows the previous session's critique as cards instead of raw JSON;
  - `/sessions/:id/scorecard`, linked from the tab.

  Older unstructured scorecards fall back to the raw JSON view.
- **How it's generated:** `backend/app/services/post_session.py`, which replaces the dead `scorecard_generator.py`.
  - One Gemini call produces the critique and the client summary.
  - Output is validated with `models/scorecard.PostSessionOutput`. It must contain all 8 competencies; if it doesn't, nothing is stored and the coach sees "try again".
  - **Grounding checks before storing:**
    - citation ids that weren't in the prompt's Context Library rows are dropped;
    - PCC markers filed under the wrong competency are dropped;
    - evidence quotes not found in the transcript are kept but marked "not found in transcript, check before relying on it".
  - A transcript that only partly parsed is flagged in the prompt and in the UI.
  - The client summary becomes a **pending Approvals draft**, created once per session. The existing human-approval rule applies.
- **Triggers** (user's choice: button + automatic):
  - **Manual:** `POST /api/sessions/{id}/analysis` (`?refresh=true` regenerates; 409 when there's no usable transcript).
  - **Automatic:** after a transcript is linked.
    - Drive and local backfills and the pack importer link by nearest session for the known client, within 2 days (`insert_transcript_and_link`).
    - The Drive webhook links only when **exactly one** session in the tenant ended in the last 2 days without a transcript, then analyses in the background. Anything ambiguous stays unlinked; we never guess which client a transcript belongs to.
- **Transcript parsing fixed** (`transcript_normalizer.py`). The real sample files previously failed:
  - Gemini "Meeting Notes" Markdown (`## Transcript` + `**Name:** text`) now parses;
  - Plaud exports skip the header, keep `[hh:mm:ss]` timestamps, ignore `[END OF RECORDING]`, and mark damaged files `partial`.
- **Prompts:** the 4 post-session templates were rewritten around `{icf_rubric}` and the numbered transcript, with a per-session-type focus. For example, 1-on-1s look at the GROW flow and agreement (3.1–3.4), and team sessions check that every voice was drawn in. Every prompt is filled with the safe `render_prompt`.
- **Changed from the plan:**
  - Gemini's `response_schema` isn't used. The SDK version handles nested schemas poorly; the prompt states the exact JSON shape and the backend validates strictly instead.
  - No Google Tasks push yet.
  - Scorecards aren't saved to Drive (traceability rows still Missing).

### Prompt library descriptions
- `prompt_templates.description` says when the prompt runs, what it uses, what it produces, and whether the output reaches the client. All 8 seeded prompts have one.
- The library shows the description under each title, with a **Copy prompt** button. The create and new-version forms have a description field; a new version keeps the previous description unless it's changed.

### Quality-of-life features taken from the R&D prototype
The prototype (`Desktop\CoahFlow Research and Development\CoachFlow`) is a mock-data AI Studio click-through, not a fork. I took only small frontend features that fit the rules:
- **Clients:** search by name or email, session-type filter chips, and "No clients match · Clear filters".
- **Calendar:**
  - sessions grouped by day ("Today", "Tomorrow", "Wednesday 23 September" plus "in 3 days"), each with its time;
  - the Need attention tile jumps to the unmatched-events list, whose explanation now matches the new matching rules.
- **Session panel:**
  - "Confidential · uses {client}'s records only";
  - copy buttons on prep points (and Copy all);
  - a count on the History tab;
  - clearer empty states.
- **Toasts** can be dismissed and have an `info` tone.

**Deliberately not taken:**
- **The commitments tracker:** it needs a backend model, and the prototype lets the AI overwrite human-confirmed statuses.
- **The "second brain synced" indicator:** it's fake in the prototype.
- **Caching client files in localStorage:** it would leak confidential notes.
- **Free-form create/delete prompts and "reset to default":** they conflict with the fixed, append-only slots.
- **The 5-part prep format:** a bigger backend change; a good next step.

### Tests
- Backend: 98 pass (ruff, mypy clean). New tests cover:
  - parser tests on the real formats;
  - `segments_to_text`;
  - `test_post_session.py`: grounding, draft once, invalid output stores nothing, no transcript, cached reuse, background trigger never raises;
  - analysis route access (403) and 409;
  - the unambiguous-session webhook link;
  - description carry-over.
- Frontend: 11 pass, including `IcfCritique.test.tsx`.

### Next steps
- Run the 2026-09-19 patch, and re-import the ICF file (see §3).
- **Try it end to end on sandbox data:** link a sample transcript to a session, open the ICF critique tab, and check the quotes and ratings read sensibly. Prompt wording may need tuning after real runs, done by posting a new template version in the prompt library.
- Later:
  - a session-end trigger for sessions whose transcript never arrives;
  - trends across sessions (ratings per competency over time);
  - the 5-part prep format;
  - Google Tasks for coach action items.

