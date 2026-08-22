# Local backfill upload directory

Drop pre-existing coaching material here for `scripts/local_backfill.py` to
push into Supabase — a one-time replacement for the Drive/OAuth-based import
(`services/drive_backfill.py`) while tenant OAuth isn't connected yet. This
directory's actual contents are gitignored (real client data never gets
committed); only this README and the folder skeleton are tracked.

```
local_backfill/
├── context-library/*      org-wide GROW/ICF docs (.md/.txt/.pdf/.docx; no prompt files)
├── client-notes/*.md      frontmatter: client: <Name matching clients.name>
├── transcripts/*.md       frontmatter: client: <Name>; optional date:, source: (plaud|gemini_meet)
└── calendar/*.json        Google Calendar API event resource shape, or a
                            list / {"items": [...]} wrapper of them
```

Frontmatter example (`client-notes/jane-doe-2026-01.md`):

```
---
client: Jane Doe
title: Session notes — 2026-01-10
---
Body content goes here...
```

Any category folder can be omitted if you have nothing for it — the script
reports 0 files for a missing subdirectory rather than failing.

Usage (from `backend/`):

```
uv run python scripts/local_backfill.py data/local_backfill --tenant-id tenant_a              # dry run — no writes
uv run python scripts/local_backfill.py data/local_backfill --tenant-id tenant_a --execute     # actually writes
```
