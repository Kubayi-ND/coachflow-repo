from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.core.config import get_settings
from app.db.repository import get_user_by_id
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, object] = {}


async def _get_jwks() -> dict[str, object]:
    """Supabase-issued JWTs are verified against Supabase's JWKS endpoint —
    no shared secret to manage or rotate. Cached in-process; Supabase rotates
    keys infrequently enough that a process restart is an acceptable refresh."""
    if not _jwks_cache:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.supabase_jwks_url, timeout=10)
            response.raise_for_status()
            _jwks_cache.update(response.json())
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    jwks = await _get_jwks()
    try:
        claims = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False},
        )
    except Exception as exc:  # jose raises several JWTError subclasses
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    user = await get_user_by_id(UUID(claims["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not provisioned")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


def assert_client_access(user: User, client_id: UUID) -> None:
    """Every service function touching a client_id must call this — enforced
    in db/repository.py, not just in route handlers, per backend/CLAUDE.md,
    so a new route can't accidentally skip the check."""
    if user.role == UserRole.ADMIN:
        return
    if client_id not in user.assigned_client_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not assigned to this client")
