from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.db.crud.user import create_user, get_user, get_user_by_telegram_id
from src.app.schemas.user import UserCreate, User
from src.app.exceptions import NotFoundError


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=200)
async def create_or_get_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await get_user_by_telegram_id(db, user_data.telegram_id)
    if existing:
        return existing
    return await create_user(db, user_data)


@router.get("/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(db, user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return user
