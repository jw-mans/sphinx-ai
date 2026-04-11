from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional

from src.app.db.models import Question
from src.app.schemas.question import QuestionCreate, QuestionUpdate


async def create_question(db: AsyncSession, question: QuestionCreate) -> Question:
    db_question = Question(**question.dict())
    db.add(db_question)
    try:
        await db.commit()
        await db.refresh(db_question)
    except Exception:
        await db.rollback()
        raise
    return db_question


async def get_question(db: AsyncSession, question_id: int) -> Optional[Question]:
    result = await db.execute(select(Question).where(Question.id == question_id))
    return result.scalars().first()


async def get_questions_by_interview(db: AsyncSession, interview_id: int) -> List[Question]:
    result = await db.execute(select(Question).where(Question.interview_id == interview_id))
    return result.scalars().all()


async def update_question(db: AsyncSession, question_id: int, question_update: QuestionUpdate) -> Optional[Question]:
    update_data = question_update.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Question)
            .where(Question.id == question_id)
            .values(**update_data)
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return await get_question(db, question_id)


async def delete_question(db: AsyncSession, question_id: int) -> bool:
    result = await db.execute(delete(Question).where(Question.id == question_id))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return result.rowcount > 0
