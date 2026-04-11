from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional

from src.app.db.models import Interview
from src.app.schemas.interview import InterviewCreate, InterviewUpdate


async def create_interview(
    db: AsyncSession, 
    interview: InterviewCreate
) -> Interview:
    db_interview = Interview(**interview.dict())
    db.add(db_interview)
    try:
        await db.commit()
        await db.refresh(db_interview)
    except Exception:
        await db.rollback()
        raise
    return db_interview


async def get_interview(
    db: AsyncSession, 
    interview_id: int
) -> Optional[Interview]:
    result = await db.execute(
        select(Interview)
        .where(Interview.id == interview_id)
    )
    return result.scalars().first()


async def get_interviews_by_user(
    db: AsyncSession, 
    user_id: int
) -> List[Interview]:
    result = await db.execute(
        select(Interview)
        .where(Interview.user_id == user_id)
    )
    return result.scalars().all()


async def update_interview(
    db: AsyncSession, 
    interview_id: int, 
    interview_update: InterviewUpdate
) -> Optional[Interview]:
    update_data = interview_update.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Interview)
            .where(Interview.id == interview_id)
            .values(**update_data)
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return await get_interview(db, interview_id)


async def delete_interview(
    db: AsyncSession, 
    interview_id: int
) -> bool:
    result = await db.execute(
        delete(Interview)
        .where(Interview.id == interview_id)
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return result.rowcount > 0
