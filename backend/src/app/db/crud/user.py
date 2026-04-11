from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import Optional

from src.app.db.models import User
from src.app.schemas.user import UserCreate, UserUpdate


async def create_user(
    db: AsyncSession, 
    user: UserCreate
) -> User:
    db_user = User(**user.dict())
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
    except Exception:
        await db.rollback()
        raise
    return db_user


async def get_user(
    db: AsyncSession, 
    user_id: int
) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
    )
    return result.scalars().first()


async def get_user_by_telegram_id(
    db: AsyncSession, 
    telegram_id: str
) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
    )
    return result.scalars().first()


async def update_user(
    db: AsyncSession, 
    user_id: int, 
    user_update: UserUpdate
) -> Optional[User]:
    update_data = user_update.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return await get_user(db, user_id)


async def delete_user(
    db: AsyncSession, 
    user_id: int
) -> bool:
    result = await db.execute(delete(User).where(User.id == user_id))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return result.rowcount > 0