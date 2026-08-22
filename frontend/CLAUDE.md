# CoachFlow — Frontend

React dashboard for the coach and admin. It is the only surface either role touches — everything the backend automates (transcript filing, AI drafting, reminders) surfaces here for review, and nothing client-facing sends without going through this UI's Approvals inbox.

## Stack

- **React 18 + TypeScript + Vite** — build tool and dev server
- **React Router 6** — routing
- **TanStack Query** — all server-state fetching/caching against the backend API; don't hand-roll `useEffect` fetch logic
- **Supabase JS client** (`@supabase/supabase-js`) — auth only (login, session refresh, JWT retrieval); it does **not** query Supabase tables directly — all data reads/writes go through the backend API so authorization logic lives in one place
- **Tailwind CSS** — utility styling, configured with the CoachFlow token palette below
- **react-hook-form + zod** — forms and validation (client onboarding, admin settings, draft editing)
- **TanStack Table** — the client list, session history, and metrics tables
- **Recharts** — the Metrics view's charts (parse success rate, token cost vs. billable time, etc.)
- **date-fns** — all date/working-day math (lead-time countdowns must count *working* days, not calendar days)
- **Vitest + React Testing Library** — unit/component tests; **Playwright** — the Approvals-inbox and login e2e flows

## Design tokens (carry the CoachFlow identity into Tailwind config)

```
paper:      #F6F5F1   (light) / #14201C (dark)
ink:        #1F2623   (light) / #E8E6DF (dark)
teal:       #2F6F62   (light) / #6FB8A5 (dark)   — primary accent
teal-soft:  #E4EEEB   (light) / #1C332C (dark)
amber:      #B97A22   (light) / #E0AC5C (dark)   — semantic: pending/attention (reminders, unmatched events)
slate:      #5B6763   (light) / #9AA6A0 (dark)   — secondary text
```

Display face: Fraunces (headings only). Body/UI face: Public Sans. Use `font-variant-numeric: tabular-nums` on every column of numbers (metrics, countdowns, token costs).

## Folder structure

```
frontend/
├── CLAUDE.md
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx              ← route definitions incl. AdminRoute guard
│   │   └── providers.tsx           ← QueryClientProvider, SupabaseAuthProvider
│   ├── features/
│   │   ├── calendar/               ← upcoming-session countdown view, per client, per tenant
│   │   ├── approvals/              ← the Approvals inbox — the most important feature in the app
│   │   ├── clients/                ← client directory + detail (Drive links, Context Library viewer)
│   │   ├── scorecards/             ← read-only ICF/GROW critique view, per session
│   │   ├── metrics/                ← admin+coach observability dashboard
│   │   └── admin/                  ← tenants, reminder rules, prompt templates, user management
│   ├── components/ui/              ← shared primitives: Button, Pill (status/tenant badges), Table, Toast
│   ├── lib/
│   │   ├── supabaseClient.ts       ← auth-only client
│   │   ├── apiClient.ts            ← fetch wrapper, attaches Bearer JWT, typed via shared/types
│   │   └── workingDays.ts          ← working-day lead-time math, matches backend's exactly
│   ├── hooks/                      ← useSession, useRole, useClients, useDrafts, etc. (TanStack Query hooks)
│   └── types/                      ← re-exports from shared/types
└── tests/
```

## Views, in the order a coach actually uses them

**Calendar** — every upcoming session across both tenants, grouped by client, with a countdown against that session type's lead time and a status chip (`upcoming` / `prep generating` / `ready for review` / `sent`). An "unmatched events" section surfaces any calendar event the backend's naming-convention scanner couldn't classify — this is the exception-handling UI for the case study's "ambiguous naming" risk, and it needs a one-click "assign session type" action so the coach isn't blocked.

**Approvals inbox** — the core loop. A list of pending `ai_drafts`, each showing: draft type (reminder / summary / questionnaire / prep email), the client, the originating **tenant** (always visible — this is a multi-tenant system and the coach needs to know which mailbox a send will come from), and an editable text area pre-filled with the AI draft. Actions: **Approve & send**, **Edit then approve**, **Reject** (with a reason, fed back as a metric). Never auto-refresh-away an item the coach has started editing.

**Clients** — directory across both tenants; a client detail page links out to their Drive folder structure (Transcripts / Context / Evaluations) and shows their Context Library entries and session-type configuration (which of the five trigger types apply to them).

**Scorecards** — read-only, per session, showing the structured ICF/GROW critique with citations back into the Context Library section it was grounded in. This view exists so the coach can sanity-check the AI isn't hallucinating a competency framework — link every claim to its source doc.

**Metrics** (admin + coach) — admin hours saved, time from session-end to draft-ready, Gemini token cost vs. billable-hour value protected, transcript parse success rate by source (`plaud` / `gemini_meet`), draft approval rate without edits, unmatched-events count. Treat this as an operations dashboard, not a report — summary tiles first, detail tables below, and encode state (a falling approval-without-edits rate) as a visual flag, not just a number.

**Admin** — tenant credential status (connected/expired, never the raw token), reminder-rule editor (lead time + naming pattern per session type), prompt template editor (the templates that replaced Obsidian — editing here changes what draft/scorecard generation actually sends to Gemini, not just a display copy), Context Library editor (org-wide or client-specific entries, each requiring a heading so the model can judge relevance), and user management (assign clients to coaches, set roles). Both the prompt template and Context Library editors are append-only: saving posts a new version rather than overwriting, with history browsable per entry.

## API integration pattern

One `apiClient.ts` wrapping `fetch`, injecting `Authorization: Bearer <supabase JWT>`, and one TanStack Query hook per resource (`useDrafts()`, `useApproveDraft()`, etc.) — hooks own their query keys and invalidate the Approvals list on approve/reject so the inbox count updates without a manual refresh. Type every response from `shared/types` (generated from the backend's OpenAPI schema — run the generator as a pre-dev script, don't hand-maintain duplicate interfaces).

## Environment variables

```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=          # backend origin, e.g. http://localhost:8000 in dev
```

## What NOT to build here

Don't call Google APIs or the Gemini API from the frontend — all of that is backend-only, both for credential security and because the tenant-isolation guarantee only holds if there's exactly one place capable of making those calls. Don't query Supabase tables directly for app data (auth only) — that keeps role/tenant authorization enforced once, in the backend, instead of duplicated in RLS policies and frontend logic that can drift apart.
