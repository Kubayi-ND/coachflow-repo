# CoachFlow — Decisions & Spec Clarifications

The official spec is [`grow-hackathon-case-study.md`](grow-hackathon-case-study.md)
and is kept verbatim. This file records how ambiguous or conflicting points in
that spec are interpreted, and product requirements agreed after it was written.
Where the code or a `CLAUDE.md` file disagrees with an entry here, this file wins;
where an entry says **pending client confirmation**, confirm it with the client
before treating it as final.

Implementation status for every spec line lives in
[`requirements-traceability.md`](requirements-traceability.md).

| ID | Decision | Status | Spec reference |
|---|---|---|---|
| D-01 | There are **four session types** (`one_on_one`, `quarterly_review`, `annual_review`, `monthly_council`) and **five workflow phases** (A–E). Phase B (post-session analysis) applies to held sessions rather than being a session type of its own. Earlier docs that say "five session types" are wrong. | Agreed | §3 A–E |
| D-02 | **Session type is not the audience.** Quarterly, annual and monthly sessions can be held with an **individual** or with a company **team**. 1-on-1s are always individual. | Agreed (2026-09-15) | §2 item 3, §2 item 6 ("company and individual") |
| D-03 | **Separation between engagements.** By default nothing from an individual's sessions, notes, transcripts or scorecards reaches a team engagement, and individuals never see each other's information. The coach may share a specific item **from an individual into a team engagement at the same company** after an explicit warning they must acknowledge; shares pin the approved version, are logged, and can be revoked (a revoke stops future use, it cannot recall an email already sent). **Individual → individual sharing is never allowed**, not even by override. Enforced in the backend, not only in the UI. | Agreed (2026-09-15/16) | §4 confidentiality |
| D-04 | **Lead times are working days**, skipping weekends **and South African public holidays**. "3 working days (72 hours)" is read as 3 working days, since the two disagree over weekends and CON-002 speaks of working-day lead times. | Pending client confirmation | §3 A, C, D, E; CON-002 |
| D-05 | **Microsoft 365 (Tenant C)**: the data model, provider interfaces and Microsoft Graph auth architecture are designed now; the live Graph integration (mail send, calendar, Teams transcripts) is built only once the client confirms it's still needed — the coach's planned migration of `grow-za.com` mail to Google may make it unnecessary. Until then CON-001 is only partly met. | Pending client confirmation | §1, CON-001 |
| D-06 | **Which history each phase uses** (replaces the earlier "same session type only" rule). Every window is limited to the **same engagement** (D-03): **A** — the immediately prior held 1-on-1 (notes and action items); **C** — monthly council sessions from the last 3 months, plus themes across the engagement's history; **D** — all held sessions from the last 12 months; **E** — held sessions from the last month. | Agreed | §3 A, C, D, E |
| D-07 | **Two outputs per pre-session phase**: an **internal coach briefing** (shown in the dashboard, never approval-gated, never emailed) and a **client-facing draft** (reminder / questionnaire / prep email) that goes through the Approvals inbox. The two must never share a draft row. | Agreed | §3 A "Internal Notification" vs "Client Communications" |
| D-08 | **Calendar titles for individual vs team quarterly/annual/monthly sessions are undecided** (the spec's title strings don't say who the session is with). Until decided, only 1-on-1s are matched to a client automatically; quarterly, annual and monthly events go to the coach's assignment queue, and an assignment can be remembered for a recurring series. Never attach an event to "the first matching attendee". | Open — needs client input | §4 ambiguous naming, ASM-001 |
| D-09 | **Schema changes go through Supabase CLI migrations** (`supabase/migrations/`), starting from a baseline of the current `backend/app/db/schema.sql`. Hand-applied SQL is retired. | Agreed | §4 state persistence |

## Open questions for the client

1. **Calendar titles (D-08):** can quarterly, annual and monthly titles include the coachee's or company's name, like 1-on-1s do (e.g. `Grow Quarterly Strategic Review [Name]`)?
2. **Lead time (D-04):** is "3 working days" correct rather than a literal 72 hours, and should South African public holidays be skipped?
3. **Microsoft 365 (D-05):** is the `grow-za.com` mailbox migrating to Google, or does the system need to send from and read Teams transcripts via Microsoft 365?
