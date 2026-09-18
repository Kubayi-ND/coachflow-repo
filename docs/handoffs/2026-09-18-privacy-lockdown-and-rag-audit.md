# Handoff — privacy lockdown and RAG audit (2026-09-18)

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

1. **The post-session path never runs.** `scorecard_generator.generate_scorecard_and_summary` has no caller, and `/webhooks/drive` stores transcripts without linking them to a session.
2. **Prior sessions are always empty.** Nothing sets `sessions.status='sent'`, and approving a draft doesn't update its session.
3. **Org-wide entries are stuffed in, not retrieved.** `build_context` loads every `client_id IS NULL` row whole.
4. **No chunking.** Each entry, even a whole PDF, is one vector.
5. **The HNSW index is unused.** The RPC reads the `DISTINCT ON` view.
6. **No relevance cutoff.** There's no similarity threshold, scores aren't returned, and there's no hybrid/keyword search or reranking.
7. **Weak queries.** The pre-session query is a fixed template (name + type); the post-session query is the transcript's head and tail at 4,000 characters each.
8. **No grounding checks.** There's no token budget, no `response_schema`, and citations are neither requested in pre-session output nor validated after generation.
9. **Admin templates can crash generation.** `str.format` on an admin-edited template raises on a stray `{`.
10. **No retrieval evaluation.** There's no golden set, recall@k or citation-faithfulness check.

### Roadmap, in order
1. **Make the loop run:** mark sessions `held` after the event or when a transcript links; link transcripts to sessions in the webhook and call the scorecard generator; build history per phase (D-06).
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
- **D-09 migrations aren't set up.** Until they are, `schema.sql` plus `app/db/patches/*.sql` is the convention. When Supabase CLI migrations land, the baseline must include this lockdown.

## 4. Related artifacts
- Design canvas documenting schema and siloing, main vs this work (private to the author, shareable from its menu): https://claude.ai/artifact/QYHvrFAFx8EurStrGtP3Ar. It predates the lockdown code; §1 above is the current state.
- `docs/requirements-traceability.md`: the rows updated for this work.
- `MIGRATION.md`: env vars and post-migration checks now include the lockdown.
