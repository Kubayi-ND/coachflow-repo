"""One-off (and safe-to-rerun) backfill: compute embeddings for
context_library rows written before the embedding column existed — e.g. the
seeded ICF/GROW org-wide entries in schema.sql. Only touches rows where
embedding is null, so running it twice is a no-op the second time.

Usage:
    uv run python scripts/backfill_context_library_embeddings.py
"""
import asyncio

from app.ai.embeddings import embed_document_content
from app.db.repository import get_supabase, rows_of


async def main() -> None:
    supabase = get_supabase()
    rows = rows_of(
        supabase.table("context_library").select("id,title,body").is_("embedding", "null").execute()
    )
    if not rows:
        print("No context_library rows need backfilling.")
        return

    for row in rows:
        embedding = await embed_document_content(row["title"], row["body"])
        supabase.table("context_library").update({"embedding": embedding}).eq("id", row["id"]).execute()
        print(f"Backfilled embedding for context_library id={row['id']} ({row['title']!r})")

    print(f"Done — backfilled {len(rows)} row(s).")


if __name__ == "__main__":
    asyncio.run(main())
