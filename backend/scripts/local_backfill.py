"""One-off admin script: push pre-existing coaching material from local disk
into Supabase, bypassing Google Drive/OAuth. See data/local_backfill/README.md
for the expected directory/frontmatter convention, and
app/services/local_backfill.py for the actual import logic.

Defaults to a dry run (reads Supabase to preview client-name matches, writes
nothing) — pass --execute to actually write.

Usage:
    uv run python scripts/local_backfill.py data/local_backfill --tenant-id tenant_a
    uv run python scripts/local_backfill.py data/local_backfill --tenant-id tenant_a --execute
    uv run python scripts/local_backfill.py data/local_backfill --tenant-id tenant_a --source transcripts --execute
"""
import argparse
import asyncio
from pathlib import Path

from app.models.imports import ImportSource
from app.services.local_backfill import run_local_backfill


async def main(tenant_id: str, upload_dir: Path, sources: set[ImportSource] | None, dry_run: bool) -> None:
    print(f"{'DRY RUN - no writes' if dry_run else 'EXECUTING - writing to Supabase'} for tenant {tenant_id!r}\n")

    results = await run_local_backfill(tenant_id, upload_dir, sources=sources, dry_run=dry_run)

    print()
    for source, counts in results.items():
        print(
            f"{source.value}: {counts['total']} file(s) - "
            f"{counts['succeeded']} succeeded, {counts['failed']} failed, {counts['unmatched']} unmatched"
        )

    if dry_run:
        print("\nThis was a dry run - re-run with --execute to write these changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("upload_dir", type=Path, help="Directory containing context-library/, client-notes/, transcripts/, calendar/ subfolders")
    parser.add_argument("--tenant-id", required=True, help="e.g. tenant_a")
    parser.add_argument(
        "--source",
        action="append",
        choices=[s.value for s in ImportSource],
        dest="sources",
        help="Repeatable; defaults to all four sources",
    )
    parser.add_argument("--execute", action="store_true", help="Actually write to Supabase (default is a dry-run preview)")
    args = parser.parse_args()

    if not args.upload_dir.is_dir():
        raise SystemExit(f"Not a directory: {args.upload_dir}")

    asyncio.run(
        main(
            tenant_id=args.tenant_id,
            upload_dir=args.upload_dir,
            sources={ImportSource(s) for s in args.sources} if args.sources else None,
            dry_run=not args.execute,
        )
    )
