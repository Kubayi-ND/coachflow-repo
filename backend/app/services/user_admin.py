"""Supabase Auth Admin calls for account provisioning and password reset.

Uses the service-role client from db.repository.get_supabase() — already
privileged for `.auth.admin.*`, no separate client needed. This is the only
module that calls these Auth Admin methods; routes call through here rather
than touching `get_supabase().auth` directly, mirroring the single-call-site
pattern backend/CLAUDE.md establishes for Gmail sends.
"""
from uuid import UUID

from app.db.repository import get_supabase


async def invite_new_user(email: str, redirect_to: str) -> UUID:
    """Creates the Supabase Auth user and emails them an account-setup link
    in one call; the returned id becomes the app-level users.id (schema.sql:
    "id must equal the auth.users id")."""
    result = get_supabase().auth.admin.invite_user_by_email(email, {"redirect_to": redirect_to})
    return UUID(result.user.id)


async def send_password_reset_email(email: str, redirect_to: str) -> None:
    get_supabase().auth.reset_password_for_email(email, {"redirect_to": redirect_to})
