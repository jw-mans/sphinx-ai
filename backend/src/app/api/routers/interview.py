from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.app.db.session import get_db
from src.app.db.crud.interview import get_interview
from src.app.dependencies import get_interview_service, get_interview_service_v2, get_current_user_id
from src.app.services import InterviewService
from src.app.schemas import InterviewCreate


router = APIRouter(prefix="/interview", tags=["interview"])


async def _require_interview_owner(
    interview_id: int,
    db: AsyncSession,
    current_user_id: int,
):
    """
    REQ-SEC-02: Fetch interview and verify the caller owns it.
    Raises 404 if interview does not exist, 403 if wrong owner.
    """
    interview = await get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail=f"Interview {interview_id} not found")
    if interview.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return interview

"""
V1 ENDPOINTS
"""

@router.post("/start")
async def start_interview(
    interview_data: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service),
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Начинает новое интервью.
    """
    if interview_data.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: user_id mismatch")

    result = await service.start_interview(
        db, interview_data.user_id, interview_data.level,
        interview_data.stack, interview_data.user_notes,
    )
    return {
        "interview_id": result["interview"].id,
        "current_question": {
            "id": result["current_question"].id,
            "text": result["current_question"].text,
            "topic": result["current_question"].topic,
            "difficulty": result["current_question"].difficulty,
        },
    }


@router.get("/{interview_id}/question")
async def get_current_question(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service),
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Возвращает текущий вопрос.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

    result = await service.get_current_question(db, interview_id)
    if not result:
        return {"message": "Interview completed"}
    question = result["question"]
    return {
        "id": question.id,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty,
    }


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: int,
    answer: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service),
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Отправляет ответ на текущий вопрос.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

    result = await service.submit_answer(
        db, interview_id,
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

"""
V2 ENDPOINTS
"""

@router.get("/{interview_id}/result")
async def get_interview_result(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service),
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Возвращает итоги интервью.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

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


# ---------------------------------------------------------------------------
# V2 endpoints (adaptive generation via LLMClientNew)
# ---------------------------------------------------------------------------

@router.get("/{interview_id}/question/v2")
async def get_current_question_v2(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    service: InterviewService = Depends(get_interview_service_v2),
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Возвращает следующий вопрос с адаптивной генерацией.
    REQ-SEC-01/02: требует JWT, проверяет владельца.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

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
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Отправляет ответ с калиброванной оценкой.
    REQ-SEC-01/02: требует JWT, проверяет владельца.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

    result = await service.submit_answer_v2(
        db, interview_id,
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
    current_user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Возвращает итоги интервью с улучшенным саммари.
    REQ-SEC-01/02: требует JWT, проверяет владельца.
    """
    await _require_interview_owner(interview_id, db, current_user_id)

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
