"""One-off migration: push the hackathon "Candidates Pack" sample data
(backend/Candidates Pack/Candidates Pack/) straight into Supabase, bypassing
both Google Drive (services/drive_backfill.py) and the local-file convention
in services/local_backfill.py — that convention expects one Markdown file per
client-notes/transcript with `client:` frontmatter, and this pack uses a
different, one-off layout (prior-notes/, transcripts/ mixing .md/.txt/.vtt,
a combined multi-tenant calendar JSON, and Context Library docs in
.docx/.pdf/.txt).

Scope decisions (see the accompanying report for the full rationale):
  - Only Google tenants (tenant_a / tenant_b) are imported. The pack's
    tenantC_microsoft_exchange calendar block and the three clients
    explicitly labelled "Tenant C" in their prior-notes (David Chen, Fatima
    Adams, Karen Bosch), plus their teams_*.vtt transcripts, are skipped —
    this repo is the Google Workspace-only iteration per root CLAUDE.md, and
    transcript_source has no 'teams' value in schema.sql.
  - "Marcus Smith"'s anonymized transcript has no client email or tenant
    marker anywhere in the pack, so no `clients` row (email NOT NULL) can be
    created for him — skipped.
  - Of "Grow Context Library", the three hackathon-administrative documents
    (case study, itinerary, solution template) and the two prompt-shaped docs
    ("Coaching evaluation prompt.docx", "Coaching Preparation Prompt.docx")
    are excluded from context_library — the former isn't coaching content,
    the latter would pollute retrieval with prompt-authoring instructions
    rather than grounding material (prompt_templates already owns that
    content, seeded in schema.sql).

Idempotent by manual existence checks (clients by tenant+email, sessions by
client+event_date, unmatched_events by tenant+summary+event_date,
context_library by title, transcripts by file_ref) rather than relying on a
DB-level unique constraint that may not exist on this project's live schema.

Usage (from backend/):
    uv run python scripts/migrate_candidates_pack.py                # dry run — no writes
    uv run python scripts/migrate_candidates_pack.py --execute       # actually writes
"""
import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.db.repository import get_supabase, get_user_by_email, row_of, rows_of
from app.models.client import Client as ClientModel
from app.models.transcript import TranscriptSource
from app.services.calendar_scanner import add_working_days, match_session_type
from app.services.client_matching import AUTO_MATCHED_SESSION_TYPES
from app.services.context_library_admin import create_context_library_entry_with_embedding
from app.services.document_extractor import _extract_docx_text, _extract_pdf_text
from app.services.drive_backfill import insert_transcript_and_link
from app.session_types_generated import SESSION_TYPES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate_candidates_pack")

PACK_DIR = Path(__file__).parent.parent / "Candidates Pack" / "Candidates Pack"
COACH_EMAIL = "anelisiwemagazi17@gmail.com"

# (name, email) per tenant, derived from calendar attendees + prior-notes,
# both of which agree on every name/email/tenant triple.
TENANT_CLIENTS: dict[str, list[tuple[str, str]]] = {
    "tenant_a": [
        ("Dineo Khumalo", "dineo@kefitapay.co.za"),
        ("Thabo Molefe", "thabo@sasekileprop.co.za"),
        ("Aisha Patel", "aisha@nurahealth.co.za"),
        ("Pieter van Wyk", "pieter@agritoro.co.za"),
    ],
    "tenant_b": [
        ("Sipho Ndlovu", "sipho@haulink.africa"),
        ("Naledi Mokoena", "naledi@tshwaerobotics.co.za"),
        ("Rui Fernandes", "rui@costafoods.co.za"),
    ],
}

CALENDAR_TENANT_KEYS = {
    "tenant_a": "tenantA_google_primary",
    "tenant_b": "tenantB_google_secondary",
}

CONTEXT_LIBRARY_FILES = [
    "GROW COACHING CORE Version 5 (1).docx",
    "ICF CCs with PCC Markers 0326 PLAIN TEXT.txt",
    "Compounding Advantage_Text_FTP.pdf",
    "iEQ9 Joss du Trevou CC.pdf",
    "Joss du Trevou Coach Profile .pdf",
]
CONTEXT_LIBRARY_EXCLUDED = [
    "Coaching evaluation prompt.docx",
    "Coaching Preparation Prompt.docx",
    "Grow Hackathon Case Study.docx",
    "Hackathon Itinerarary.pdf",
    "Hackathon-solution-template 20 August Update _.docx",
]

# filename token -> (client name substring, transcript source)
TRANSCRIPT_FILES = {
    "gemini_naledi_2026-07-30.md": ("naledi", TranscriptSource.GEMINI_MEET),
    "gemini_sipho_2026-07-27.md": ("sipho", TranscriptSource.GEMINI_MEET),
    "plaud_dineo_2026-07-26.txt": ("dineo", TranscriptSource.PLAUD),
    "plaud_thabo_2026-07-24.txt": ("thabo", TranscriptSource.PLAUD),
    "plaud_pieter_CORRUPTED_2026-07-31.txt": ("pieter", TranscriptSource.PLAUD),
}
TRANSCRIPT_FILES_SKIPPED = [
    "teams_david_2026-07-29.vtt",       # Tenant C / Microsoft — out of scope
    "teams_karen_2026-07-28.vtt",       # Tenant C / Microsoft — out of scope
    "20260529 Coaching Session Marcus Smith - Anonymized.md",  # no client email/tenant identifiable
]

PRIOR_NOTES_SKIPPED = ["david", "fatima", "karen"]  # Tenant C / Microsoft — out of scope


def _extract_text(path: Path) -> str:
    if path.suffix == ".docx":
        text = _extract_docx_text(path.read_bytes())
    elif path.suffix == ".pdf":
        text = _extract_pdf_text(path.read_bytes())
    else:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # The ICF competencies .txt is a classic-Mac export (Mac Roman,
            # bare CR line endings); decoding it as UTF-8 garbles every
            # curly quote and dash the critique prompt quotes back.
            text = raw.decode("mac_roman")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\x00", "")  # Postgres text columns reject NUL bytes some PDF extractions leave in


def _only_match(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Exactly one client, or None — never the first of several."""
    unique = {row["id"]: row for row in matches}
    return next(iter(unique.values())) if len(unique) == 1 else None


def _rel(path: Path) -> str:
    return path.relative_to(PACK_DIR).as_posix()


async def ensure_clients(coach_user_id: str, *, dry_run: bool) -> dict[str, dict[str, Any]]:
    """Returns {email: client_row} for every client in TENANT_CLIENTS, creating
    any that don't already exist for their tenant."""
    supabase = get_supabase()
    by_email: dict[str, dict[str, Any]] = {}

    for tenant_id, roster in TENANT_CLIENTS.items():
        existing_rows = rows_of(supabase.table("clients").select("*").eq("tenant_id", tenant_id).execute())
        existing_by_email = {row["email"]: row for row in existing_rows}

        for name, email in roster:
            if email in existing_by_email:
                by_email[email] = existing_by_email[email]
                continue

            if dry_run:
                print(f"[dry-run] would create client: {name} <{email}> ({tenant_id})")
                by_email[email] = {"id": None, "name": name, "email": email, "tenant_id": tenant_id}
                continue

            result = (
                supabase.table("clients")
                .insert(
                    {
                        "name": name,
                        "email": email,
                        "coach_user_id": coach_user_id,
                        "tenant_id": tenant_id,
                        "session_types": ["one_on_one"],
                    }
                )
                .execute()
            )
            row = row_of(result)
            assert row is not None
            by_email[email] = row
            print(f"created client: {name} <{email}> ({tenant_id})")

    return by_email


async def link_clients_to_coach(coach_user_id: str, client_ids: list[str], *, dry_run: bool) -> None:
    supabase = get_supabase()
    user_row = row_of(supabase.table("users").select("assigned_client_ids").eq("id", coach_user_id).execute())
    assert user_row is not None
    current = set(user_row["assigned_client_ids"] or [])
    updated = sorted(current | set(client_ids))
    if updated == sorted(current):
        return
    if dry_run:
        print(f"[dry-run] would set assigned_client_ids to {len(updated)} client(s) for coach {coach_user_id}")
        return
    supabase.table("users").update({"assigned_client_ids": updated}).eq("id", coach_user_id).execute()
    print(f"linked {len(updated)} client(s) to coach {coach_user_id}")


async def import_calendar(clients_by_email: dict[str, dict[str, Any]], *, dry_run: bool) -> None:
    supabase = get_supabase()
    calendar_path = PACK_DIR / "calendar" / "calendar_events.json"
    data = json.loads(calendar_path.read_text(encoding="utf-8"))

    reminder_rules = {row["session_type"]: row["lead_time_working_days"] for row in rows_of(supabase.table("reminder_rules").select("*").execute())}

    for tenant_id, calendar_key in CALENDAR_TENANT_KEYS.items():
        events = data.get(calendar_key, [])
        existing_sessions = (
            rows_of(supabase.table("sessions").select("client_id, event_date").eq("tenant_id", tenant_id).execute())
            if not dry_run
            else []
        )
        existing_unmatched = (
            rows_of(supabase.table("unmatched_events").select("raw_event_summary, event_date").eq("tenant_id", tenant_id).execute())
            if not dry_run
            else []
        )

        for event in events:
            summary = event.get("summary", "")
            start_raw = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            if not start_raw:
                continue
            event_date = datetime.fromisoformat(start_raw)

            session_type = match_session_type(summary)
            if session_type is None:
                already = any(
                    r["raw_event_summary"] == summary and datetime.fromisoformat(r["event_date"]) == event_date
                    for r in existing_unmatched
                )
                if already:
                    continue
                if dry_run:
                    print(f"[dry-run] would file unmatched_event: {summary!r} ({tenant_id})")
                    continue
                supabase.table("unmatched_events").insert(
                    {"tenant_id": tenant_id, "raw_event_summary": summary, "event_date": event_date.isoformat()}
                ).execute()
                print(f"unmatched_event: {summary!r} ({tenant_id})")
                continue

            attendee_emails = {a.get("email", "").strip().lower() for a in event.get("attendees", []) if not a.get("organizer")}
            client = _only_match(
                [c for c in clients_by_email.values() if c["email"].lower() in attendee_emails]
                if session_type in AUTO_MATCHED_SESSION_TYPES
                else []
            )
            if client is None:
                # Not a 1-on-1 with exactly one known client: it may be a team
                # session (D-08), so it goes to the coach's queue, never to
                # the first matching attendee.
                if not dry_run:
                    supabase.table("unmatched_events").insert(
                        {"tenant_id": tenant_id, "raw_event_summary": summary, "event_date": event_date.isoformat()}
                    ).execute()
                logger.warning("Session-type event %r (%s) not auto-matched to one client; filed as unmatched", summary, tenant_id)
                continue

            if dry_run:
                print(f"[dry-run] would create session: {client['name']} / {session_type.value} @ {event_date.isoformat()}")
                continue

            already = any(
                r["client_id"] == client["id"] and datetime.fromisoformat(r["event_date"]) == event_date
                for r in existing_sessions
            )
            if already:
                continue

            lead_time = reminder_rules.get(session_type.value, SESSION_TYPES[session_type].lead_time_working_days)
            trigger_date = add_working_days(event_date, lead_time)
            supabase.table("sessions").insert(
                {
                    "client_id": client["id"],
                    "type": session_type.value,
                    "tenant_id": tenant_id,
                    "event_date": event_date.isoformat(),
                    "trigger_date": trigger_date.isoformat(),
                    "status": "upcoming",
                    "external_event_id": event.get("id"),
                }
            ).execute()
            print(f"session: {client['name']} / {session_type.value} @ {event_date.isoformat()}")


async def import_context_library(*, dry_run: bool) -> None:
    supabase = get_supabase()
    dir_path = PACK_DIR / "Grow Context Library"
    existing_titles = {r["title"] for r in rows_of(supabase.table("context_library").select("title").is_("client_id", "null").execute())} if not dry_run else set()

    for filename in CONTEXT_LIBRARY_FILES:
        path = dir_path / filename
        title = path.stem
        if title in existing_titles:
            continue
        if dry_run:
            print(f"[dry-run] would create org-wide context_library entry: {title!r}")
            continue
        text = _extract_text(path)
        await create_context_library_entry_with_embedding(None, title, text)
        print(f"context_library (org-wide): {title!r}")
        await asyncio.sleep(5)


async def import_prior_notes(clients_by_email: dict[str, dict[str, Any]], *, dry_run: bool) -> None:
    supabase = get_supabase()
    dir_path = PACK_DIR / "prior-notes"
    clients_by_name = {row["name"].casefold(): row for row in clients_by_email.values()}

    for path in sorted(dir_path.glob("*.md")):
        token = path.stem.split("_")[0].lower()
        if token in PRIOR_NOTES_SKIPPED:
            continue
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        client = _only_match([c for name, c in clients_by_name.items() if token in name.split()])
        if client is None:
            logger.warning("No single client match for prior-notes file %s (token=%r)", path.name, token)
            continue

        if dry_run:
            print(f"[dry-run] would create client-note context_library entry for {client['name']}: {title!r}")
            continue

        if not dry_run:
            existing = rows_of(supabase.table("context_library").select("id").eq("client_id", client["id"]).eq("title", title).execute())
            if existing:
                continue
        await create_context_library_entry_with_embedding(client["id"], title, text)
        print(f"context_library (client={client['name']}): {title!r}")
        await asyncio.sleep(5)


async def import_transcripts(clients_by_email: dict[str, dict[str, Any]], *, dry_run: bool) -> None:
    supabase = get_supabase()
    dir_path = PACK_DIR / "transcripts"
    clients_by_name = {row["name"].casefold(): row for row in clients_by_email.values()}

    for filename, (token, source) in TRANSCRIPT_FILES.items():
        path = dir_path / filename
        client = _only_match([c for name, c in clients_by_name.items() if token in name.split()])
        if client is None:
            logger.warning("No single client match for transcript file %s (token=%r)", filename, token)
            continue

        rel_id = _rel(path)
        if dry_run:
            print(f"[dry-run] would insert transcript for {client['name']}: {filename} (source={source.value})")
            continue

        existing = rows_of(supabase.table("transcripts").select("id").eq("file_ref", rel_id).execute())
        if existing:
            continue

        date_str = filename.split("_")[-1].removesuffix(".md").removesuffix(".txt")
        created_time_iso = f"{date_str}T00:00:00+00:00" if len(date_str) == 10 else None
        raw_bytes = path.read_bytes()
        await insert_transcript_and_link(ClientModel(**client), rel_id, source, raw_bytes, created_time_iso)
        print(f"transcript: {client['name']} <- {filename} (source={source.value})")


async def main(dry_run: bool) -> None:
    print(f"{'DRY RUN - no writes' if dry_run else 'EXECUTING - writing to Supabase'}\n")

    coach = await get_user_by_email(COACH_EMAIL)
    if coach is None:
        raise SystemExit(f"No user found with email {COACH_EMAIL!r} — create the account first via Admin > Users.")
    print(f"Target coach account: {coach.email} ({coach.id}, role={coach.role.value})\n")

    clients_by_email = await ensure_clients(str(coach.id), dry_run=dry_run)
    client_ids = [c["id"] for c in clients_by_email.values() if c["id"] is not None]
    await link_clients_to_coach(str(coach.id), client_ids, dry_run=dry_run)

    await import_calendar(clients_by_email, dry_run=dry_run)
    await import_context_library(dry_run=dry_run)
    await import_prior_notes(clients_by_email, dry_run=dry_run)
    await import_transcripts(clients_by_email, dry_run=dry_run)

    print("\nSkipped (out of scope for this Google-only iteration):")
    print(f"  - Context Library docs excluded: {', '.join(CONTEXT_LIBRARY_EXCLUDED)}")
    print(f"  - Prior-notes clients excluded (Tenant C): {', '.join(PRIOR_NOTES_SKIPPED)}")
    print(f"  - Transcript files excluded: {', '.join(TRANSCRIPT_FILES_SKIPPED)}")

    if dry_run:
        print("\nThis was a dry run - re-run with --execute to write these changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execute", action="store_true", help="Actually write to Supabase (default is a dry-run preview)")
    args = parser.parse_args()
    asyncio.run(main(dry_run=not args.execute))
