from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().token_vault_encryption_key.encode())


def encrypt_refresh_token(raw_token: str) -> str:
    return _fernet().encrypt(raw_token.encode()).decode()


def decrypt_refresh_token(encrypted_token: str) -> str:
    """Decrypts a tenant's refresh token. Callers must not cache the result
    beyond the current request — see integrations/google/auth.py."""
    return _fernet().decrypt(encrypted_token.encode()).decode()
