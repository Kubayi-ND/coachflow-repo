import logging

from fastapi import APIRouter, Depends, status

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.repository import complete_password_reset
from app.models.user import PasswordResetRequest, User
from app.services.user_admin import send_password_reset_email

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(body: PasswordResetRequest) -> None:
    """Unauthenticated by design. Always returns 204 regardless of whether
    the email is registered — a 404-vs-200 response would let an attacker
    probe which emails have accounts."""
    settings = get_settings()
    try:
        await send_password_reset_email(body.email, f"{settings.app_base_url}/set-password")
    except Exception:
        logger.exception("Password reset email failed to send")


@router.post("/complete-password-reset", response_model=User)
async def complete_password_reset_route(user: User = Depends(get_current_user)) -> User:
    """Called by SetPasswordPage right after supabase.auth.updateUser
    succeeds, so a temp-password account's forced-reset flag is cleared —
    that call only changes Supabase Auth, it never touches our `users` row."""
    updated = await complete_password_reset(user.id)
    assert updated is not None
    return updated
