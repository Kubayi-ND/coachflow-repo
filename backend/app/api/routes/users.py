from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user_profile(user: User = Depends(get_current_user)) -> User:
    return user
