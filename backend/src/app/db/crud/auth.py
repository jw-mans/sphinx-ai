from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.db.models.user import User
from src.app.core.security import hash_password, verify_password
from src.app.db.crud.user import get_user_by_telegram_id  # reuse, don't duplicate


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_web_user(db: AsyncSession, email: str, password: str, name: str) -> User:
    user = User(email=email, hashed_password=hash_password(password), name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_or_get_telegram_user(db: AsyncSession, telegram_id: str, name: Optional[str]) -> User:
    existing = await get_user_by_telegram_id(db, telegram_id)
    if existing:
        return existing
    user = User(telegram_id=telegram_id, name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
