from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.db.repository import list_clients_for_user
from app.models.client import Client
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[Client])
async def get_clients(user: User = Depends(get_current_user)) -> list[Client]:
    return await list_clients_for_user(user)
