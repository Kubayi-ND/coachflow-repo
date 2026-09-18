from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TenantOAuthConfig(BaseSettings):
    client_id: str
    client_secret: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    supabase_jwks_url: str

    gemini_api_key: str

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    token_vault_encryption_key: str

    google_oauth_client_id_tenant_a: str
    google_oauth_client_secret_tenant_a: str
    google_oauth_client_id_tenant_b: str
    google_oauth_client_secret_tenant_b: str

    apps_script_webhook_shared_secret: str
    app_base_url: str = "http://localhost:8000"
    # Comma-separated browser origins allowed to call the API (the deployed
    # frontend). Local dev goes through Vite's /api proxy, so it needs none.
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def supabase_jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def tenant_oauth_configs(self) -> dict[str, TenantOAuthConfig]:
        return {
            "tenant_a": TenantOAuthConfig(
                client_id=self.google_oauth_client_id_tenant_a,
                client_secret=self.google_oauth_client_secret_tenant_a,
            ),
            "tenant_b": TenantOAuthConfig(
                client_id=self.google_oauth_client_id_tenant_b,
                client_secret=self.google_oauth_client_secret_tenant_b,
            ),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
