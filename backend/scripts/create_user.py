"""One-off admin script: provision a user account.

Creates the Supabase Auth account and the matching `users` row (per
db/schema.sql's "id must equal the auth.users id" mirror). Password is read
from the NEW_USER_PASSWORD env var, never a CLI flag, so it doesn't land in
shell history.

Usage:
    export NEW_USER_PASSWORD='...'
    uv run python scripts/create_user.py --email someone@example.com --role general
    unset NEW_USER_PASSWORD
"""
import argparse
import asyncio
import os
import sys
from uuid import UUID

from app.db.repository import create_user_record, get_supabase
from app.models.user import UserRole


async def main(email: str, role: UserRole, password: str) -> None:
    supabase = get_supabase()

    auth_response = supabase.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    auth_user = auth_response.user
    if auth_user is None:
        print("Failed to create Supabase Auth user.", file=sys.stderr)
        sys.exit(1)

    try:
        user = await create_user_record(user_id=UUID(auth_user.id), email=email, role=role)
    except Exception:
        supabase.auth.admin.delete_user(auth_user.id)
        raise

    print(f"Created user id={user.id} email={user.email} role={user.role.value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[r.value for r in UserRole], default=UserRole.GENERAL.value)
    args = parser.parse_args()

    password = os.environ.get("NEW_USER_PASSWORD")
    if not password:
        print("Set NEW_USER_PASSWORD in the environment before running this script.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(email=args.email, role=UserRole(args.role), password=password))
