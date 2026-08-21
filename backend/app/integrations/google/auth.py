"""The only module that decrypts a tenant's OAuth refresh token — and it does
so per-request, never caching the decrypted value beyond the request
lifecycle, per backend/CLAUDE.md's credential-vault rules.
"""
from google.oauth2.credentials import Credentials

from app.core.config import get_settings
from app.core.crypto import decrypt_refresh_token
from app.db.repository import get_supabase, rows_of

_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/tasks",
]


class TenantCredentialError(Exception):
    pass


async def get_tenant_credentials(tenant_id: str) -> Credentials:
    """Fetches and decrypts this tenant's refresh token, returning short-lived
    OAuth credentials scoped to that tenant only. Callers must not persist the
    returned object beyond the current request/job iteration."""
    result = (
        get_supabase()
        .table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = rows_of(result)
    if not rows or not rows[0].get("encrypted_refresh_token"):
        raise TenantCredentialError(f"No connected credentials for tenant {tenant_id!r}")

    tenant_row = rows[0]
    settings = get_settings()
    oauth_config = settings.tenant_oauth_configs[tenant_id]
    refresh_token = decrypt_refresh_token(tenant_row["encrypted_refresh_token"])

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=oauth_config.client_id,
        client_secret=oauth_config.client_secret,
        scopes=_SCOPES,
    )
