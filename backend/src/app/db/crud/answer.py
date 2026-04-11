from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional

from src.app.db.models import Answer
from src.app.schemas.answer import AnswerCreate, AnswerUpdate


async def create_answer(
    db: AsyncSession, 
    answer: AnswerCreate
) -> Answer:
    db_answer = Answer(**answer.dict())
    db.add(db_answer)
    try:
        await db.commit()
        await db.refresh(db_answer)
    except Exception:
        await db.rollback()
        raise
    return db_answer


async def get_answer(
    db: AsyncSession, 
    answer_id: int
) -> Optional[Answer]:
    result = await db.execute(
        select(Answer)
        .where(Answer.id == answer_id)
    )
    return result.scalars().first()


async def get_answers_by_question(
    db: AsyncSession, 
    question_id: int
) -> List[Answer]:
    result = await db.execute(
        select(Answer)
        .where(Answer.question_id == question_id)
    )
    return result.scalars().all()


async def update_answer(
    db: AsyncSession, 
    answer_id: int, 
    answer_update: AnswerUpdate
) -> Optional[Answer]:
    update_data = answer_update.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Answer)
            .where(Answer.id == answer_id)
            .values(**update_data)
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return await get_answer(db, answer_id)


async def delete_answer(db: AsyncSession, answer_id: int) -> bool:
    result = await db.execute(
        delete(Answer)
        .where(Answer.id == answer_id)
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return result.rowcount > 0
