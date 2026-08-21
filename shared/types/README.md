# shared/types

`session-types.json` is the single source of truth for the five (currently four
distinct calendar-naming, soon possibly more) recurring session types described in
the root `CLAUDE.md`. Both packages generate from it instead of re-typing the
naming strings and lead times:

- `scripts/generate-session-types.ts` → `frontend/src/types/sessionTypes.generated.ts`
- `scripts/generate_session_types.py` → `backend/app/session_types_generated.py`

Regenerate after editing the JSON:

```bash
cd shared/types
node scripts/generate-session-types.ts   # or: pnpm --filter frontend run gen:session-types
python scripts/generate_session_types.py
```

Do not hand-edit either generated file — edit `session-types.json` and regenerate.
The generated TS file also backs the OpenAPI-derived request/response types the
frontend imports for everything else (`shared/types` is where the OpenAPI
generator's output lands too, once the backend schema exists to generate from).
