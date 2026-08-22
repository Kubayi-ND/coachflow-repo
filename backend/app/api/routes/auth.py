import logging

from fastapi import APIRouter, status

from app.core.config import get_settings
from app.models.user import PasswordResetRequest
from app.services.user_admin import send_password_reset_email

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(body: PasswordResetRequest) -> None:
    """Unauthenticated by design. Always returns 204 regardless of whether
    the email is registered — a 404-vs-204 response would let an attacker
    probe which emails have accounts."""
    settings = get_settings()
    try:
        await send_password_reset_email(body.email, f"{settings.app_base_url}/set-password")
    except Exception:
        logger.exception("Password reset email failed to send")
