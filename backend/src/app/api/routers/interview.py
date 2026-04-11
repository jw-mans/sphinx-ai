from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.app.db.session import get_db
from src.app.dependencies import get_interview_service, get_interview_service_v2
from src.app.services import InterviewService
from src.app.schemas import InterviewCreate


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/start")
async def start_interview(
    interview_data: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service)
) -> Dict[str, Any]:
    """
    Начинает новое интервью
    """
    result = await service.start_interview(db, interview_data.user_id, interview_data.level, interview_data.stack, interview_data.user_notes)
    return {
        "interview_id": result["interview"].id,
        "current_question": {
            "id": result["current_question"].id,
            "text": result["current_question"].text,
            "topic": result["current_question"].topic,
            "difficulty": result["current_question"].difficulty
        }
    }


@router.get("/{interview_id}/question")
async def get_current_question(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service)
) -> Dict[str, Any]:
    """
    Возвращает текущий вопрос для интервью
    """
    result = await service.get_current_question(db, interview_id)
    if not result:
        return {"message": "Interview completed"}
    question = result["question"]
    return {
        "id": question.id,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty
    }


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    answer: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service)
) -> Dict[str, Any]:
    """
    Отправляет ответ на текущий вопрос
    """
    result = await service.submit_answer(
        db,
        interview_id,
        answer.get("text", ""),
        answer.get("code")
    )
    evaluation = result["evaluation"]
    return {
        "evaluation": {
            "score": evaluation.score_json,
            "feedback": evaluation.feedback,
            "weak_topics": evaluation.weak_topics
        },
        "next_question": result.get("next_question")
    }


@router.get("/{interview_id}/result")
async def get_interview_result(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service)
) -> Dict[str, Any]:
    """
    Возвращает итоги интервью
    """
    result = await service.get_interview_result(db, interview_id)
    return {
        "average_score": result["average_score"],
        "summary": result.get("summary"),
        "questions_results": [
            {
                "question": r["question"],
                "answer": r["answer"],
                "score": r["score"],
                "feedback": r["feedback"],
                "weak_topics": r["weak_topics"]
            } for r in result["questions_results"]
        ]
    }


# V2 endpoints (adaptive generation via LLMClientNew) 

@router.get("/{interview_id}/question/v2")
async def get_current_question_v2(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service_v2),
) -> Dict[str, Any]:
    """
    Возвращает следующий вопрос с адаптивной генерацией:
    учитывает avg score, тип вопроса по ротации и семантическую дедупликацию.
    """
    result = await service.get_current_question_v2(db, interview_id)
    if not result:
        return {"message": "Interview completed"}
    question = result["question"]
    return {
        "id": question.id,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty,
    }


@router.post("/{interview_id}/answer/v2")
async def submit_answer_v2(
    interview_id: int,
    answer: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service_v2),
) -> Dict[str, Any]:
    """
    Отправляет ответ с калиброванной оценкой:
    передаёт running avg score в evaluator для стабильного скоринга.
    """
    result = await service.submit_answer_v2(
        db,
        interview_id,
        answer.get("text", ""),
        answer.get("code"),
    )
    evaluation = result["evaluation"]
    return {
        "evaluation": {
            "score": evaluation.score_json,
            "feedback": evaluation.feedback,
            "weak_topics": evaluation.weak_topics,
        },
        "next_question": result.get("next_question"),
    }


@router.get("/{interview_id}/result/v2")
async def get_interview_result_v2(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service_v2),
) -> Dict[str, Any]:
    """
    Возвращает итоги интервью с улучшенным саммари:
    включает анализ тренда производительности по ходу сессии.
    """
    result = await service.get_interview_result(db, interview_id)
    return {
        "average_score": result["average_score"],
        "summary": result.get("summary"),
        "questions_results": [
            {
                "question": r["question"],
                "answer": r["answer"],
                "score": r["score"],
                "feedback": r["feedback"],
                "weak_topics": r["weak_topics"],
            }
            for r in result["questions_results"]
        ],
    }
