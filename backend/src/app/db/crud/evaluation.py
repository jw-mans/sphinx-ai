from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional

from src.app.db.models import Evaluation
from src.app.schemas.evaluation import EvaluationCreate, EvaluationUpdate


async def create_evaluation(db: AsyncSession, evaluation: EvaluationCreate) -> Evaluation:
    db_evaluation = Evaluation(**evaluation.dict())
    db.add(db_evaluation)
    await db.commit()
    await db.refresh(db_evaluation)
    return db_evaluation


async def get_evaluation(db: AsyncSession, evaluation_id: int) -> Optional[Evaluation]:
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    return result.scalars().first()


async def get_evaluations_by_answer(db: AsyncSession, answer_id: int) -> List[Evaluation]:
    result = await db.execute(select(Evaluation).where(Evaluation.answer_id == answer_id))
    return result.scalars().all()


async def update_evaluation(db: AsyncSession, evaluation_id: int, evaluation_update: EvaluationUpdate) -> Optional[Evaluation]:
    update_data = evaluation_update.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Evaluation)
            .where(Evaluation.id == evaluation_id)
            .values(**update_data)
        )
        await db.commit()
    return await get_evaluation(db, evaluation_id)


async def delete_evaluation(db: AsyncSession, evaluation_id: int) -> bool:
    result = await db.execute(delete(Evaluation).where(Evaluation.id == evaluation_id))
    await db.commit()
    return result.rowcount > 0