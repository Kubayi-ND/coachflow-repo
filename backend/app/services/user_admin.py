"""Supabase Auth Admin calls for account provisioning and password reset.

Uses the service-role client from db.repository.get_supabase() — already
privileged for `.auth.admin.*`, no separate client needed. This is the only
module that calls these Auth Admin methods; routes call through here rather
than touching `get_supabase().auth` directly, mirroring the single-call-site
pattern backend/CLAUDE.md establishes for Gmail sends.
"""
import secrets
from uuid import UUID

from app.db.repository import get_supabase


async def create_user_with_temp_password(email: str) -> tuple[UUID, str]:
    """Creates the Supabase Auth user directly with a generated one-time
    password, rather than emailing an account-setup link — this project's
    Supabase instance has no outbound email configured, so invite_user_by_email
    silently fails after already creating the Auth account (the orphaned-user
    bug this replaced). The caller is responsible for handing the returned
    password to the admin exactly once and for rolling back the Auth account
    (auth.admin.delete_user) if the follow-up app-level users insert fails."""
    password = secrets.token_urlsafe(12)
    result = get_supabase().auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    if result.user is None:
        raise RuntimeError(f"Failed to create Supabase Auth user for {email}")
    return UUID(result.user.id), password


async def send_password_reset_email(email: str, redirect_to: str) -> None:
    get_supabase().auth.reset_password_for_email(email, {"redirect_to": redirect_to})
