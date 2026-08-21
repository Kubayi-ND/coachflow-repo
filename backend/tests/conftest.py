import os

import pytest

# Populate required Settings fields with dummy values before app.core.config
# is imported anywhere in the test session — CI must never make a live call
# to Google or Gemini (backend/CLAUDE.md testing notes).
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWKS_URL", "https://example.supabase.co/auth/v1/jwks")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TOKEN_VAULT_ENCRYPTION_KEY", "kX9mF3qP7vN2wR8tY5uJ4hL6bC1dE0zA9sG2iK3oM4Q=")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID_TENANT_A", "tenant-a-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET_TENANT_A", "tenant-a-secret")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID_TENANT_B", "tenant-b-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET_TENANT_B", "tenant-b-secret")
os.environ.setdefault("APPS_SCRIPT_WEBHOOK_SHARED_SECRET", "test-webhook-secret")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
