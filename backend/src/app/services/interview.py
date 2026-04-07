from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from fastapi import HTTPException

from src.app.db.crud import (
    create_interview,
    get_interview,
    create_question,
    get_questions_by_interview,
    create_answer,
    get_answers_by_question,
)
from src.app.schemas import InterviewCreate, QuestionCreate, AnswerCreate
from src.app.core.llm_client import LLMClient


class InterviewService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def start_interview(self, db: AsyncSession, user_id: int, level: str, stack: str) -> Dict[str, Any]:
        """Создаёт новое интервью и генерирует первый вопрос"""
        # Создать интервью
        interview_data = InterviewCreate(user_id=user_id, level=level, stack=stack)
        interview = await create_interview(db, interview_data)

        # Сгенерировать первый вопрос
        question_data = await self.llm_client.generate_question(level, stack)
        question_create = QuestionCreate(
            interview_id=interview.id,
            text=question_data["text"],
            topic=question_data["topic"],
            difficulty=level
        )
        question = await create_question(db, question_create)

        return {
            "interview": interview,
            "current_question": question
        }

    async def get_current_question(self, db: AsyncSession, interview_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает текущий вопрос для интервью (последний без ответа или с ответом без оценки)"""
        questions = await get_questions_by_interview(db, interview_id)
        if not questions:
            return None

        # Найти последний вопрос без оценки
        for question in reversed(questions):
            answers = await get_answers_by_question(db, question.id)
            if answers:
                # Проверить, есть ли оценка для последнего ответа
                # Для простоты, если ответ есть, считаем вопрос отвеченным
                continue
            else:
                return {"question": question}

        return None  # Все вопросы отвечены

    async def submit_answer(self, db: AsyncSession, interview_id: int, answer_text: str, code: str = None) -> Dict[str, Any]:
        """Отправляет ответ на текущий вопрос и оценивает его"""
        current = await self.get_current_question(db, interview_id)
        if not current:
            raise HTTPException(status_code=400, detail="No current question")

        question = current["question"]

        # Создать ответ
        answer_create = AnswerCreate(
            question_id=question.id,
            text=answer_text,
            code=code
        )
        answer = await create_answer(db, answer_create)

        # Оценить ответ через LLM
        evaluation_data = await self.llm_client.evaluate_answer(question.text, answer_text + (code or ""))

        # Создать оценку
        from src.app.db.crud import create_evaluation
        from src.app.schemas import EvaluationCreate
        evaluation_create = EvaluationCreate(
            answer_id=answer.id,
            score_json=evaluation_data["score"],
            feedback=evaluation_data["feedback"],
            weak_topics=evaluation_data.get("weak_topics", [])
        )
        evaluation = await create_evaluation(db, evaluation_create)

        # Опционально: сгенерировать следующий вопрос на основе weak_topics
        # Для MVP просто вернуть результат

        return {
            "answer": answer,
            "evaluation": evaluation,
            "next_question": None  # Пока без адаптации
        }

    async def get_interview_result(self, db: AsyncSession, interview_id: int) -> Dict[str, Any]:
        """Возвращает итоги интервью"""
        interview = await get_interview(db, interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        questions = await get_questions_by_interview(db, interview_id)
        results = []

        total_score = {"correctness": 0, "optimality": 0, "complexity": 0, "explanation": 0, "gaps": 0}
        count = 0

        for question in questions:
            answers = await get_answers_by_question(db, question.id)
            if answers:
                answer = answers[0]  # Предполагаем один ответ
                # Получить оценку
                from src.app.db.crud import get_evaluations_by_answer
                evaluations = await get_evaluations_by_answer(db, answer.id)
                if evaluations:
                    eval_data = evaluations[0]
                    score = eval_data.score_json
                    for key in total_score:
                        total_score[key] += score.get(key, 0)
                    count += 1
                    results.append({
                        "question": question.text,
                        "answer": answer.text,
                        "score": score,
                        "feedback": eval_data.feedback,
                        "weak_topics": eval_data.weak_topics
                    })

        if count > 0:
            avg_score = {k: v / count for k, v in total_score.items()}
        else:
            avg_score = total_score

        return {
            "interview": interview,
            "average_score": avg_score,
            "questions_results": results
        }
