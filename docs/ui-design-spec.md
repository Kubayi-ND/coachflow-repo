# CoachFlow UI Design Specification

> Inspired by the Dribbble Task Management Dashboard aesthetic (shot 25241984): left sidebar navigation, elevated card system, prominent stat tiles, rich status indicators, and activity-feed patterns — adapted to CoachFlow's executive coaching domain.

---

## 1. Design philosophy

The current UI uses a top horizontal nav bar and flat list layouts. This spec shifts to a **left sidebar shell** with a **card-first content area**, matching the visual language of modern task/work management tools. Every change stays within the existing Tailwind token system — new tokens are additive only.

Key principles:
- **Sidebar-first navigation** — vertical rail gives the coach a stable spatial anchor; nav items never reflow across screen widths.
- **Card elevation hierarchy** — surfaces are layered (page background → section card → inline widget) so the coach always knows what they're acting on.
- **Stat tiles at the top of every main view** — the coach sees the count of what needs attention before scrolling.
- **Status is always a colour, not just a label** — every pill, countdown, and session row encodes urgency visually.
- **Human-in-the-loop affordances are prominent** — Approve / Reject actions are full-width buttons on large cards, not small links.

---

## 2. Design tokens (extend existing)

The current palette stays unchanged. Add three new surface tokens and a set of elevation shadows.

### 2.1 New CSS custom properties

```css
/* index.css — append to :root / .dark blocks */

/* Light */
:root {
  /* existing tokens unchanged */
  --color-surface:    255 255 255;    /* card surface, above paper */
  --color-surface-2:  242 241 237;    /* inset well (e.g. textarea bg) */
  --color-border:     220 218 212;    /* dividers, card outlines */
  --color-sidebar-bg: 31  45  41;     /* sidebar always dark-tone */
  --color-sidebar-fg: 204 214 210;    /* sidebar text (on dark bg) */
  --color-sidebar-accent: 111 184 165; /* active nav item highlight */
}

/* Dark */
.dark {
  /* existing tokens unchanged */
  --color-surface:    26  40  36;
  --color-surface-2:  20  32  28;    /* same as paper, creates depth by border */
  --color-border:     52  70  64;
  --color-sidebar-bg: 14  24  20;    /* even darker than dark paper */
  --color-sidebar-fg: 154 166 160;
  --color-sidebar-accent: 111 184 165;
}
```

### 2.2 Tailwind config additions

```ts
// tailwind.config.ts — extend the colors object
surface: {
  DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
  2: "rgb(var(--color-surface-2) / <alpha-value>)",
},
border: "rgb(var(--color-border) / <alpha-value>)",
sidebar: {
  bg:     "rgb(var(--color-sidebar-bg) / <alpha-value>)",
  fg:     "rgb(var(--color-sidebar-fg) / <alpha-value>)",
  accent: "rgb(var(--color-sidebar-accent) / <alpha-value>)",
},
```

### 2.3 Elevation / shadow scale

Add to `tailwind.config.ts` under `theme.extend.boxShadow`:

```ts
boxShadow: {
  card:    "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
  cardmd:  "0 4px 12px 0 rgb(0 0 0 / 0.10), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
  panel:   "0 8px 24px 0 rgb(0 0 0 / 0.14), 0 4px 8px -4px rgb(0 0 0 / 0.10)",
},
```

---

## 3. Layout shell (`NavShell.tsx`)

### 3.1 Current layout

```
┌─────────────────────────────────────────────────────┐
│  CoachFlow [nav links ................] [buttons]    │  ← horizontal header
├─────────────────────────────────────────────────────┤
│  <main content px-6 py-6>                           │
└─────────────────────────────────────────────────────┘
```

### 3.2 Target layout

```
┌──────────┬────────────────────────────────────────┐
│          │  ┌─ top bar ─────────────────────────┐  │
│ SIDEBAR  │  │  Page title      🔔  avatar  ☀️   │  │
│  240px   │  └───────────────────────────────────┘  │
│  always  │                                          │
│  dark    │  <main content area, bg-paper>           │
│  bg      │  max-w-7xl mx-auto px-8 py-8            │
│          │                                          │
└──────────┴────────────────────────────────────────┘
```

### 3.3 Sidebar specification

**Dimensions:** `w-60` (240 px) fixed, full viewport height, `overflow-y-auto`.

**Background:** `bg-sidebar-bg` (dark in both themes — sidebar is always dark).

**Logo block** (top, 64 px tall):
- `px-5 py-5`
- Wordmark: "CoachFlow" in `font-display text-base text-white`
- Beneath the wordmark: `text-[10px] tracking-widest uppercase text-sidebar-fg/60` — "Executive Coaching"

**Nav section label** (rendered above each group):
```
CLASS: px-5 pt-6 pb-2 text-[10px] font-semibold uppercase tracking-widest text-sidebar-fg/50
```

**Nav item** (link row):
```
CLASS (inactive): flex items-center gap-3 px-4 mx-2 py-2.5 rounded-lg
                  text-sm text-sidebar-fg/80 hover:bg-white/5 transition-colors
CLASS (active):   … bg-sidebar-accent/15 text-sidebar-accent font-medium
ICON:             16×16 px inline SVG, stroke-current, flex-shrink-0
BADGE (optional): ml-auto rounded-full bg-amber/20 text-amber text-[10px] px-1.5 py-0.5
                  tabular-nums — show count of pending items for Approvals nav item
```

**Nav groups and order:**

```
[no label — primary coach actions]
  📅  Upcoming sessions        (/  )
  ✅  Approvals                (/approvals)  [badge: pending count]
  👥  Clients                  (/clients)

[label: LIBRARY]
  📚  Context Library          (/context-library)       [admin + general roles]

[label: ADMIN]           [admin role only]
  👤  Users                    (/admin/users)
  📥  Import                   (/admin/imports)

[bottom — always visible, pushed to bottom with mt-auto]
  ⚙️  Account                  (/account)
  [theme toggle icon button]  — sun/moon icon, no text label
```

**Bottom user block** (inside sidebar, `mt-auto border-t border-white/10 px-4 py-4`):
- Avatar circle: `h-8 w-8 rounded-full bg-sidebar-accent/30 text-sidebar-accent text-xs flex items-center justify-center` — initials from user email
- Name/email in `text-xs text-sidebar-fg/70`, single line, truncated
- Log out icon button to the right: `text-sidebar-fg/50 hover:text-sidebar-fg`

### 3.4 Top bar (per-page)

Height `h-16`, `bg-surface border-b border-border`.

Left: **Page title** — the `<h1>` for the current view, rendered as `text-lg font-display text-ink` (eliminates the inline `<h1>` from individual page components — title is hoisted here via React context or a `usePageTitle` hook).

Right cluster (gap-3, items-center):
- Notification bell icon (24 px) — `text-slate hover:text-ink`, badge count for unread drafts
- Theme toggle — sun/moon icon button, `text-slate hover:text-ink`
- Avatar button (32 px circle) → links to `/account`

---

## 4. Typography adjustments

No font changes (Fraunces + Public Sans stays). Apply the following sizing conventions consistently:

| Role | Classes |
|---|---|
| Page section heading | `text-sm font-semibold uppercase tracking-wide text-slate` |
| Card title | `text-base font-medium text-ink` |
| Card meta / secondary | `text-xs text-slate` |
| Stat tile value | `text-3xl tabular-nums font-display text-ink` |
| Stat tile label | `text-xs text-slate mt-1` |
| Pill / badge | `text-[11px] font-medium` |
| Nav item | `text-sm` |
| Body copy in drawers | `text-sm leading-6 text-ink` |

---

## 5. Card system

Replace all `border border-slate/20 rounded-lg` patterns with the elevated card system.

### 5.1 Card variants

**Base card** — standard content container:
```
bg-surface rounded-xl shadow-card border border-border p-5
```

**Stat tile** — top-of-view KPI block:
```
bg-surface rounded-xl shadow-card border border-border px-5 py-4
```

**Attention card** — amber-bordered, for unmatched events or overdue actions:
```
bg-amber/5 rounded-xl border border-amber/30 px-5 py-4
```

**Inset well** — inside a card, for textareas and code blocks:
```
bg-surface-2 rounded-lg border border-border
```

**Hover-interactive card** (session row, client row):
```
bg-surface rounded-xl shadow-card border border-border
hover:shadow-cardmd hover:border-teal/30 transition-all duration-150 cursor-pointer
```

---

## 6. View-by-view redesign

### 6.1 Calendar / Upcoming sessions view

**Stat tiles strip** (4 tiles, `grid-cols-4 gap-4 mb-8`):

Each tile:
```
┌─────────────────────┐
│  [icon 20px]        │
│                     │
│  12                 │  ← text-3xl tabular-nums font-display
│  Active clients     │  ← text-xs text-slate mt-1
└─────────────────────┘
```

Icon colour: teal for positive/ready, amber for attention, slate for neutral.

Tile icons:
- Active clients → people icon (slate)
- Upcoming sessions → calendar icon (slate)
- Prep ready → check-circle icon (teal)
- Need attention → alert-triangle icon (amber, only if count > 0)

**Session list section** (`space-y-6`):

Section header row:
```
flex items-center justify-between mb-3
  LEFT:  Client name — text-sm font-semibold text-ink
         Tenant pill — Pill tone="neutral" text-[10px]
  RIGHT: "3 sessions" — text-xs text-slate
```

Session row card (`hover-interactive card` variant, `p-4`):
```
┌─────────────────────────────────────────────────────────┐
│  LEFT COLUMN (flex-1)                                   │
│    Session type label     text-sm font-medium text-ink  │
│    "in 12 calendar days · 3 working days to trigger"    │
│       text-xs text-slate tabular-nums                   │
│                                                         │
│  RIGHT COLUMN (flex items-center gap-3)                 │
│    [Status pill]   [Countdown chip]   [View prep →]     │
└─────────────────────────────────────────────────────────┘
```

**Countdown chip** — new component, lives next to the status pill:
```
CLASS: inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] tabular-nums
  > 5 working days:   bg-teal-soft text-teal
  2–5 working days:   bg-amber/15 text-amber
  < 2 working days:   bg-red-100 text-red-700 (dark: bg-red-950/40 text-red-400)
  0 or overdue:       bg-red-500 text-white
```

**"View prep →" link** — `text-xs font-medium text-teal hover:text-teal/70`

**Unmatched events section** — rendered below the session list only when count > 0:

Section header: `flex items-center gap-2 mb-3`
- Alert triangle icon (16 px, text-amber)
- "Unmatched events" in `text-sm font-semibold text-amber`
- `(N)` count badge

Each unmatched event row — `attention card` variant (`mb-2`):
```
flex items-center justify-between
  LEFT:  raw event title, text-sm text-ink
  RIGHT: <Select> styled to match new card surface
```

**Session prep drawer** — right-side sheet, unchanged behaviour but restyled:

Sheet: `fixed inset-0 z-20 bg-ink/40` overlay → `aside` with `bg-surface w-full max-w-2xl shadow-panel`

Header: `px-6 py-5 border-b border-border`
- Session type label: `text-[10px] uppercase tracking-widest text-slate`
- Title: `text-xl font-display mt-1`
- Description: `text-sm text-slate mt-1`

Tab bar: `flex gap-0 mt-4 border-b border-border` — each tab `px-4 pb-3 text-sm border-b-2`:
- active: `border-teal text-teal font-medium`
- inactive: `border-transparent text-slate hover:text-ink`

Content area: `flex-1 overflow-y-auto px-6 py-6 bg-surface`

---

### 6.2 Approvals inbox

**Header row** (`flex items-center justify-between mb-6`):
- Left: pending count badge — `inline-flex items-center gap-2 text-sm text-slate` with `<span class="rounded-full bg-amber/15 text-amber text-xs px-2 py-0.5 tabular-nums">{n} pending</span>`
- Right: filter chips (show all / reminder / summary / questionnaire / prep email) — `flex gap-2`, pill-shaped toggle buttons

**Draft card** (`base card` variant, `space-y-4`):

```
┌─────────────────────────────────────────────────────────────┐
│  CARD HEADER (flex items-start justify-between)              │
│    LEFT:                                                     │
│      [Draft type pill]  [Tenant pill]                        │
│      Client name        text-sm font-medium text-ink mt-1   │
│      Session type       text-xs text-slate                   │
│    RIGHT:                                                     │
│      "Scheduled send: Dec 15" text-xs text-slate tabular-nums│
├─────────────────────────────────────────────────────────────┤
│  BODY — <Textarea> using inset-well classes                  │
│    min-h-36, full width                                      │
│    Character / word count: text-[10px] text-slate text-right│
│    mt-1.5                                                    │
├─────────────────────────────────────────────────────────────┤
│  ACTIONS (flex items-center gap-3)                           │
│    [Approve & send]   variant="primary"  flex-1             │
│    [Reject]           variant="danger"   w-auto             │
│                                                             │
│  REJECT STATE — replaces action bar:                        │
│    <Input placeholder="Reason…" flex-1>                     │
│    [Confirm reject] variant="danger"                        │
│    [Cancel]         variant="secondary"                     │
└─────────────────────────────────────────────────────────────┘
```

**Empty state** (inbox clear):
```
flex flex-col items-center py-20 text-center
  Check-circle icon: 48px, text-teal/40
  "Inbox is clear" — text-base font-medium text-ink mt-4
  "All drafts have been reviewed." — text-sm text-slate mt-1
```

---

### 6.3 Clients directory

**Page layout:** two-column on md+: `grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6`

Left column — **client list panel** (`base card`, `overflow-hidden`):
- Search input at top: `px-4 pt-4 pb-3 border-b border-border`
  - `<Input type="search" placeholder="Search clients…" className="w-full text-sm">`
- List of clients: `divide-y divide-border`
  - Each row: `flex items-center gap-3 px-4 py-3 hover:bg-surface-2 cursor-pointer transition-colors`
    - Avatar: `h-9 w-9 rounded-full bg-teal-soft text-teal text-xs flex items-center justify-center flex-shrink-0` — 2-letter initials
    - Name: `text-sm font-medium text-ink`
    - Tenant: `text-[10px] text-slate`
    - Active indicator (if selected): left border `border-l-2 border-teal` on the row

Right column — **client detail** (`space-y-5`):
- Header card: client name (`text-2xl font-display`), tenant pill, Drive link button
- Stats row: 3 tiles — Total sessions, Next session in N days, Context entries
- Context Library section (collapsible) — `base card`
- Session history table — `base card`

---

### 6.4 Context Library

**Two-pane layout** (`grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6`):

Left pane — **category sidebar** (`base card p-0 overflow-hidden`):
- Category list: ICF Competencies, GROW Model, Client Profiles, Prompt Templates
- Each: `flex items-center justify-between px-4 py-3 text-sm hover:bg-surface-2 cursor-pointer`
- Active: `bg-teal-soft text-teal font-medium`
- Entry count badge: `text-[10px] text-slate tabular-nums`

Right pane — entries list + editor:
- **New entry button**: `Button variant="primary" size="sm"` top-right of the pane header
- Entry card: `hover-interactive card mb-3`
  - Heading: `text-sm font-medium text-ink`
  - Preview: first 120 chars, `text-xs text-slate mt-1 line-clamp-2`
  - Footer: `text-[10px] text-slate/60 mt-3` — "v3 · updated Dec 10"
- **Editor** (when entry selected): full-width `base card` with version history in a collapsible at the bottom

---

### 6.5 Scorecards view

**Layout:** single column, `max-w-3xl mx-auto`

**Scorecard card** structure:

```
┌─ base card ─────────────────────────────────────────────┐
│  HEADER                                                  │
│    ICF/GROW badge pill (teal)                            │
│    Competency title   text-lg font-display               │
│    "Source: [Context Library entry title]" — text-xs link│
├─────────────────────────────────────────────────────────┤
│  SCORE BAR                                              │
│    Label: "Demonstrated"  ─────────────────  "4 / 5"   │
│    Progress bar: h-1.5 rounded-full                     │
│      bg-surface-2 (track) / bg-teal (fill)              │
├─────────────────────────────────────────────────────────┤
│  EVIDENCE                                               │
│    Blockquote with left border: border-l-2 border-teal  │
│    pl-4 text-sm leading-6 text-ink italic               │
│                                                         │
│  COACHING NOTE                                          │
│    text-sm text-slate leading-6                         │
└─────────────────────────────────────────────────────────┘
```

---

### 6.6 Metrics / Admin dashboard (admin role)

**Stat tile strip** (3-col on md, 6-col on xl, `gap-4 mb-8`):

Each tile layout:
```
┌────────────────────────┐
│  ICON AREA             │
│  [icon in tinted ring] │  ← h-10 w-10 rounded-full bg-teal-soft flex items-center justify-center
│                        │     icon: 20px, text-teal
│  72%                   │  ← text-3xl tabular-nums font-display
│  Approval rate         │  ← text-xs text-slate mt-1
│                        │
│  ↑ 4% vs last month    │  ← text-[11px] text-teal/80 mt-2 (or amber for decline)
└────────────────────────┘
```

**Charts section** (`grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8`):

Each chart card: `base card` with:
- Card header: title `text-sm font-semibold text-ink` + optional period selector `<Select>`
- Chart area: Recharts `ResponsiveContainer height={200}`
- Chart colours: teal for primary series, amber for secondary/attention, slate for grid/axis labels

**Detail tables section**: TanStack Table inside a `base card`, with:
- Table header row: `bg-surface-2 text-[11px] uppercase tracking-wide text-slate`
- Alternating row bg: none (dividers only, `divide-y divide-border`)
- Status cells use `<Pill>` component (unchanged API, new visual treatment — see §7)

---

## 7. Component updates

### 7.1 `Button.tsx`

Add `size` prop: `sm` (h-7 px-3 text-xs), `md` (h-9 px-4 text-sm, default), `lg` (h-11 px-5 text-sm).

Variant `primary` (current default, no change needed beyond naming the variant explicitly):
```
bg-teal text-white hover:bg-teal/90 focus-visible:ring-teal/40
rounded-lg font-medium transition-colors
```

Variant `secondary`:
```
bg-surface border border-border text-ink hover:bg-surface-2
rounded-lg font-medium transition-colors
```

Variant `danger`:
```
bg-red-600 text-white hover:bg-red-700 rounded-lg font-medium transition-colors
(dark: bg-red-700 hover:bg-red-600)
```

Variant `ghost`:
```
text-slate hover:text-ink hover:bg-surface-2 rounded-lg font-medium transition-colors
```

### 7.2 `Pill.tsx`

Expand tone set and increase visual weight:

| tone | light classes | dark classes |
|---|---|---|
| `teal` | `bg-teal-soft text-teal` | `bg-teal/15 text-teal` |
| `amber` | `bg-amber/15 text-amber` | `bg-amber/20 text-amber` |
| `neutral` | `bg-border text-slate` | `bg-surface-2 text-slate` |
| `danger` | `bg-red-100 text-red-700` | `bg-red-950/40 text-red-400` |

Base classes (all tones): `inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium`

### 7.3 `Input.tsx` and `Textarea.tsx`

Replace border styling:
```
OLD: border-slate/20
NEW: border-border bg-surface-2 focus:border-teal focus:ring-1 focus:ring-teal/20
     rounded-lg
```

### 7.4 `Table.tsx`

Wrap output in `base card` shell (pass `className` down so callers can opt out).

Header cells: `text-[11px] uppercase tracking-wide text-slate bg-surface-2 px-4 py-2.5`

Body cells: `px-4 py-3 text-sm` with `divide-y divide-border` rows.

### 7.5 New: `StatTile.tsx`

```tsx
interface StatTileProps {
  label: string;
  value: string | number;
  icon?: ReactNode;       // 20px SVG icon
  tone?: "teal" | "amber" | "neutral";
  trend?: string;         // e.g. "↑ 4% vs last month"
  trendTone?: "teal" | "amber";
}
```

```
CLASS: bg-surface rounded-xl shadow-card border border-border px-5 py-4
icon ring: h-10 w-10 rounded-full flex items-center justify-center mb-3
  tone=teal:   bg-teal-soft  icon text-teal
  tone=amber:  bg-amber/15   icon text-amber
  tone=neutral: bg-surface-2 icon text-slate
value: text-3xl tabular-nums font-display text-ink
label: text-xs text-slate mt-1
trend: text-[11px] mt-2 (trendTone=teal → text-teal, amber → text-amber)
```

### 7.6 New: `CountdownChip.tsx`

```tsx
interface CountdownChipProps {
  workingDaysLeft: number;
}
```

Colour tiers (above §6.1 countdown chip spec) — self-contained component that computes its own class string from `workingDaysLeft`.

### 7.7 `Skeleton.tsx`

Update base class:
```
OLD: bg-slate/20 animate-pulse rounded
NEW: bg-surface-2 animate-pulse rounded-lg
```

---

## 8. Navigation badge (pending count)

The Approvals nav item should show a badge with the count of pending drafts. Pull this from the same `useDrafts()` query result already used on the Approvals page — the query cache makes it zero-cost.

```tsx
// In NavShell sidebar nav item for /approvals:
const { data: drafts } = useDrafts();
const pendingCount = drafts?.length ?? 0;

// Badge (only render when pendingCount > 0):
<span className="ml-auto rounded-full bg-amber/20 text-amber text-[10px] px-1.5 py-0.5 tabular-nums">
  {pendingCount}
</span>
```

---

## 9. Responsive behaviour

| Breakpoint | Sidebar | Content |
|---|---|---|
| `< md` (< 768 px) | Hidden; replaced by a hamburger → slide-over drawer | Full width |
| `md` (768–1279 px) | Collapsed icon rail, `w-16`, icons only, tooltips on hover | Full width minus 64 px |
| `lg+` (≥ 1280 px) | Full expanded sidebar `w-60` | Remainder |

Collapsed rail icon items: centred 20 px icon, no text. Active item: `bg-sidebar-accent/15` background square `rounded-lg`.

Mobile slide-over: same `bg-sidebar-bg` sidebar overlaid full-height, `w-72`, with a close × button top-right.

---

## 10. Spacing grid

Use an 8 px base grid throughout:
- Section gaps: `gap-6` (24 px) between major sections
- Card internal padding: `p-5` (20 px) standard, `p-4` for compact rows
- Between stat tiles: `gap-4` (16 px)
- Between form fields: `space-y-4` (16 px)
- Between inline elements: `gap-2` or `gap-3` (8–12 px)

---

## 11. Motion / transitions

Keep interactions subtle — this is a tool, not a marketing site.

| Element | Transition |
|---|---|
| Hover-interactive card | `transition-all duration-150` |
| Sidebar nav item bg | `transition-colors duration-100` |
| Button states | `transition-colors duration-100` |
| Drawer/sheet open | `translate-x-full → translate-x-0`, `duration-250 ease-out` |
| Drawer/sheet close | reverse, `duration-200 ease-in` |
| Skeleton shimmer | `animate-pulse` (Tailwind built-in) |

No spring physics, no layout animations — the coach works fast and animation that delays feedback is a friction tax.

---

## 12. Accessibility notes

- Sidebar nav items: `role="link"`, active item gets `aria-current="page"`.
- Collapsed rail: each icon button gets an `aria-label` matching the full nav item label.
- Mobile drawer: `role="dialog" aria-modal="true" aria-label="Navigation"`, focus trap while open, `Escape` closes it.
- Stat tiles: each tile's value + label together form a `<dl><dt>…</dt><dd>…</dd></dl>` pair so screen readers announce "Active clients: 12" rather than "12 Active clients".
- Countdown chip: `aria-label="3 working days to trigger"` on the element (the colour alone is not sufficient).
- Draft textarea: `aria-label="Draft body for {draftType} — {clientName}"`.
- Progress bar in scorecard: `role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={5}`.

---

## 13. File change checklist

Files that need to be created or modified to implement this spec:

| File | Change |
|---|---|
| `src/index.css` | Add `--color-surface`, `--color-surface-2`, `--color-border`, `--color-sidebar-*` tokens to `:root` and `.dark` |
| `tailwind.config.ts` | Add `surface`, `border`, `sidebar` colour keys; add `boxShadow` scale; add `borderRadius` `xl` alias |
| `src/app/NavShell.tsx` | Full rewrite: vertical sidebar + top bar layout |
| `src/components/ui/Button.tsx` | Add `size` prop; rename variants to `primary` / `secondary` / `danger` / `ghost` |
| `src/components/ui/Pill.tsx` | Add `danger` tone; update base classes |
| `src/components/ui/Input.tsx` | Update border + bg classes |
| `src/components/ui/Textarea.tsx` | Update border + bg classes |
| `src/components/ui/Skeleton.tsx` | Update base class |
| `src/components/ui/Table.tsx` | Wrap in card shell; update header/row classes |
| `src/components/ui/StatTile.tsx` | New component |
| `src/components/ui/CountdownChip.tsx` | New component |
| `src/features/calendar/CalendarView.tsx` | Replace `QuickStats` with `StatTile` grid; update session rows to hover-interactive cards; add `CountdownChip` |
| `src/features/approvals/ApprovalsInbox.tsx` | Restyle `DraftRow` to new card; add filter chips; add empty-state |
| `src/features/clients/ClientsDirectory.tsx` | Two-column layout with search + avatar list |
| `src/features/clients/ClientDetail.tsx` | Stat row with 3 `StatTile` components |
| `src/features/scorecards/ScorecardView.tsx` | Score bar + evidence blockquote layout |
| `src/features/context-library/ContextLibraryPage.tsx` | Two-pane layout |
| `src/hooks/useDrafts.ts` | Confirm `useDrafts()` is exported and safe to call from NavShell for badge count |
