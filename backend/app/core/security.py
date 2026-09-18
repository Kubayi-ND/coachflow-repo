from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.core.config import get_settings
from app.db.repository import get_context_library_group_client_id, get_session_by_id, get_user_by_id
from app.models.session import Session
from app.models.user import User, UserRole, UserStatus

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
        # Supabase access tokens carry aud="authenticated" and
        # iss="<project url>/auth/v1"; checking both rejects tokens minted for
        # another project or audience that happen to share a signing key.
        claims = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=get_settings().supabase_jwt_issuer,
        )
    except Exception as exc:  # jose raises several JWTError subclasses
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    user = await get_user_by_id(UUID(claims["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not provisioned")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


async def require_coach_or_admin(user: User = Depends(get_current_user)) -> User:
    """Allow coaching staff to use the shared context and prompt library."""
    if user.role not in (UserRole.ADMIN, UserRole.GENERAL):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach access required")
    return user


def assert_client_access(user: User, client_id: UUID) -> None:
    """The per-client gate for `general` users. Call it (directly, or via the
    assert_*_access helpers below) in every route that reads or writes one
    client's data; list endpoints instead filter with
    accessible_client_ids(). Admins pass through."""
    if user.role == UserRole.ADMIN:
        return
    if client_id not in user.assigned_client_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not assigned to this client")


def accessible_client_ids(user: User) -> list[UUID] | None:
    """Client ids a list query must be restricted to — None means unrestricted
    (admin). Mirrors assert_client_access for the many-rows case."""
    if user.role == UserRole.ADMIN:
        return None
    return list(user.assigned_client_ids)


async def assert_session_access(user: User, session_id: UUID) -> Session:
    """Loads a session and checks the user may see its client. Everything
    hanging off a session (drafts, scorecards, prep) goes through this."""
    session = await get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    assert_client_access(user, session.client_id)
    return session


async def assert_context_library_group_access(user: User, entry_group_id: UUID) -> UUID | None:
    """Returns the entry's client_id (None = org-wide). Org-wide entries are
    readable by every coach but only writable by admins — see
    assert_context_library_write_access."""
    found, client_id = await get_context_library_group_client_id(entry_group_id)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Context Library entry not found")
    if client_id is not None:
        assert_client_access(user, client_id)
    return client_id


def assert_context_library_write_access(user: User, client_id: UUID | None) -> None:
    """Org-wide entries reach every client's AI prompt, so only admins may
    create or edit them; a coach may only write to an assigned client."""
    if client_id is None:
        if user.role != UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can write org-wide entries")
        return
    assert_client_access(user, client_id)
