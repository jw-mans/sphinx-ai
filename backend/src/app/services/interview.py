from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List

from src.app.db.crud import (
    create_interview,
    get_interview,
    create_question,
    get_questions_by_interview,
    create_answer,
    get_answers_by_question,
    create_evaluation,
    get_evaluations_by_answer,
)
from src.app.db.crud.interview import get_interviews_by_user
from src.app.db.crud.user import get_user
from src.app.db.models import Question, Answer, Evaluation
from src.app.schemas import InterviewCreate, QuestionCreate, AnswerCreate, EvaluationCreate
from src.app.core.llm_client import LLMClient
from src.app.exceptions import NotFoundError, ConflictError

TOTAL_QUESTIONS = 5


class InterviewService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def start_interview(self, db: AsyncSession,
        user_id: int,
        level: str,
        stack: str,
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создаёт новое интервью и генерирует первый вопрос
        """
        user = await get_user(db, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        interview_data = InterviewCreate(user_id=user_id, level=level, stack=stack, user_notes=user_notes)
        interview = await create_interview(db, interview_data)

        question_data = await self.llm_client.generate_question(
            level, stack, user_notes=user_notes
        )
        question = await create_question(db, QuestionCreate(
            interview_id=interview.id,
            text=question_data["text"],
            topic=question_data["topic"],
            difficulty=level,
        ))

        return {"interview": interview, "current_question": question}

    async def get_current_question(self, db: AsyncSession,
        interview_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Возвращает текущий вопрос. Если все отвечены — генерирует следующий (до лимита).
        """
        interview = await get_interview(db, interview_id)
        if not interview:
            raise NotFoundError(f"Interview {interview_id} not found")

        questions = await get_questions_by_interview(db, interview_id)

        unanswered = await self._find_unanswered(db, questions)
        if unanswered:
            return {"question": unanswered}

        if len(questions) >= TOTAL_QUESTIONS:
            return None  # Интервью завершено

        # Генерируем следующий вопрос, учитывая слабые темы и уже заданные
        weak_topics = await self._collect_weak_topics(db, questions)
        asked_questions = [q.text for q in questions if q.text]
        weak_hint = weak_topics[0] if weak_topics else None

        question_data = await self.llm_client.generate_question(
            interview.level, interview.stack,
            weak_topic_hint=weak_hint,
            asked_questions=asked_questions,
            user_notes=interview.user_notes,
        )
        question = await create_question(db, QuestionCreate(
            interview_id=interview_id,
            text=question_data["text"],
            topic=question_data["topic"],
            difficulty=interview.level,
        ))
        return {"question": question}

    async def submit_answer(self, db: AsyncSession,
        interview_id: int,
        answer_text: str,
        code: str = None
    ) -> Dict[str, Any]:
        """
        Отправляет ответ на текущий вопрос и оценивает его
        """
        interview = await get_interview(db, interview_id)
        if not interview:
            raise NotFoundError(f"Interview {interview_id} not found")

        questions = await get_questions_by_interview(db, interview_id)
        question = await self._find_unanswered(db, questions)
        if not question:
            raise ConflictError("No unanswered questions in this interview")

        answer = await create_answer(db, AnswerCreate(
            question_id=question.id,
            text=answer_text,
            code=code,
        ))

        evaluation_data = await self.llm_client.evaluate_answer(
            question.text,
            answer_text + (f"\n\nКод:\n{code}" if code else ""),
        )

        evaluation = await create_evaluation(db, EvaluationCreate(
            answer_id=answer.id,
            score_json=evaluation_data["score"],
            feedback=evaluation_data["feedback"],
            weak_topics=evaluation_data.get("weak_topics", []),
        ))

        return {"answer": answer, "evaluation": evaluation}

    async def get_interview_result(self, db: AsyncSession,
        interview_id: int
    ) -> Dict[str, Any]:
        """
        Возвращает итоги интервью.
        Использует selectinload для устранения N+1 запросов (3 запроса вместо 2N+1).
        """
        interview = await get_interview(db, interview_id)
        if not interview:
            raise NotFoundError(f"Interview {interview_id} not found")

        # Single eager-load: questions → answers → evaluations
        stmt = (
            select(Question)
            .where(Question.interview_id == interview_id)
            .options(
                selectinload(Question.answers).selectinload(Answer.evaluations)
            )
        )
        result = await db.execute(stmt)
        questions = result.scalars().unique().all()

        results = []
        total_score: Dict[str, float] = {
            "correctness": 0.0, "optimality": 0.0,
            "complexity": 0.0, "explanation": 0.0, "gaps": 0.0,
        }
        count = 0

        for question in questions:
            if not question.answers:
                continue
            answer = question.answers[0]
            if not answer.evaluations:
                continue
            eval_data = answer.evaluations[0]
            score = eval_data.score_json
            for key in total_score:
                total_score[key] += score.get(key, 0)
            count += 1
            results.append({
                "question": question.text,
                "answer": answer.text,
                "score": score,
                "feedback": eval_data.feedback,
                "weak_topics": eval_data.weak_topics,
            })

        avg_score = {k: v / count for k, v in total_score.items()} if count > 0 else total_score

        summary = None
        if results:
            summary = await self.llm_client.generate_session_summary(
                interview.level, interview.stack, results
            )

        return {
            "interview": interview,
            "average_score": avg_score,
            "questions_results": results,
            "summary": summary,
        }

    # -----------------------------------------------------------------------
    # V2 methods (adaptive, semantic-aware generation via LLMClientNew)
    # -----------------------------------------------------------------------

    async def get_current_question_v2(
        self,
        db: AsyncSession,
        interview_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Like get_current_question but passes adaptive context to the LLM.
        """
        interview = await get_interview(db, interview_id)
        if not interview:
            raise NotFoundError(f"Interview {interview_id} not found")

        questions = await get_questions_by_interview(db, interview_id)

        unanswered = await self._find_unanswered(db, questions)
        if unanswered:
            return {"question": unanswered}

        if len(questions) >= TOTAL_QUESTIONS:
            return None

        # Build adaptive context from answered questions
        asked_texts: List[str] = []
        asked_qa_history: List[Dict[str, Any]] = []
        score_sum: Dict[str, float] = {"correctness": 0, "optimality": 0, "complexity": 0, "explanation": 0, "gaps": 0}
        answered_count = 0

        for q in questions:
            answers = await get_answers_by_question(db, q.id)
            if not answers:
                continue
            evals = await get_evaluations_by_answer(db, answers[0].id)
            if not evals:
                continue
            score = evals[0].score_json
            asked_texts.append(q.text)
            asked_qa_history.append({
                "question": q.text,
                "answer": answers[0].text,
                "score": score,
            })
            for k in score_sum:
                score_sum[k] += score.get(k, 0)
            answered_count += 1

        avg_score: Optional[float] = None
        if answered_count > 0:
            total = sum(score_sum.values()) / len(score_sum)
            avg_score = total / answered_count

        type_index = len(questions) % len(["conceptual", "practical", "debug"])
        next_type = ["conceptual", "practical", "debug"][type_index]

        weak_topics = await self._collect_weak_topics(db, questions)
        weak_hint = weak_topics[0] if weak_topics else None

        question_data = await self.llm_client.generate_question(
            interview.level,
            interview.stack,
            weak_topic_hint=weak_hint,
            asked_questions=asked_texts,
            user_notes=interview.user_notes,
            avg_score=avg_score,
            next_question_type=next_type,
            asked_qa_history=asked_qa_history,
        )
        question = await create_question(db, QuestionCreate(
            interview_id=interview_id,
            text=question_data["text"],
            topic=question_data["topic"],
            difficulty=interview.level,
        ))
        return {"question": question}

    async def submit_answer_v2(
        self,
        db: AsyncSession,
        interview_id: int,
        answer_text: str,
        code: str = None,
    ) -> Dict[str, Any]:
        """
        Like submit_answer but passes the running average score to the evaluator.
        """
        interview = await get_interview(db, interview_id)
        if not interview:
            raise NotFoundError(f"Interview {interview_id} not found")

        questions = await get_questions_by_interview(db, interview_id)
        question = await self._find_unanswered(db, questions)
        if not question:
            raise ConflictError("No unanswered questions in this interview")

        score_vals: List[float] = []
        for q in questions:
            if q.id == question.id:
                continue
            answers = await get_answers_by_question(db, q.id)
            if not answers:
                continue
            evals = await get_evaluations_by_answer(db, answers[0].id)
            if evals:
                score = evals[0].score_json
                score_vals.append(sum(score.values()) / len(score))

        prior_avg: Optional[float] = sum(score_vals) / len(score_vals) if score_vals else None

        answer = await create_answer(db, AnswerCreate(
            question_id=question.id,
            text=answer_text,
            code=code,
        ))

        evaluation_data = await self.llm_client.evaluate_answer(
            question.text,
            answer_text + (f"\n\nКод:\n{code}" if code else ""),
            prior_avg_score=prior_avg,
        )

        evaluation = await create_evaluation(db, EvaluationCreate(
            answer_id=answer.id,
            score_json=evaluation_data["score"],
            feedback=evaluation_data["feedback"],
            weak_topics=evaluation_data.get("weak_topics", []),
        ))

        return {"answer": answer, "evaluation": evaluation}

    # -----------------------------------------------------------------------
    # Analytics / Phase 4
    # -----------------------------------------------------------------------

    async def get_user_history(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns a summary list of all past interviews for the user (newest first).
        Uses selectinload — no N+1 queries.
        """
        interviews = await get_interviews_by_user(db, user_id)
        history: List[Dict[str, Any]] = []

        for interview in interviews:
            stmt = (
                select(Question)
                .where(Question.interview_id == interview.id)
                .options(
                    selectinload(Question.answers).selectinload(Answer.evaluations)
                )
            )
            res = await db.execute(stmt)
            questions = res.scalars().unique().all()

            score_sum = 0.0
            evaluated = 0
            for q in questions:
                if not q.answers:
                    continue
                evals = q.answers[0].evaluations
                if not evals:
                    continue
                s = evals[0].score_json
                score_sum += sum(s.values()) / len(s)
                evaluated += 1

            history.append({
                "interview_id": interview.id,
                "level": interview.level,
                "stack": interview.stack,
                "created_at": interview.created_at.isoformat(),
                "status": interview.status,
                "questions_count": len(questions),
                "average_score": round(score_sum / evaluated, 2) if evaluated > 0 else None,
            })

        history.sort(key=lambda x: x["created_at"], reverse=True)
        return history

    async def get_competency_profile(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Aggregates 5-criteria scores across ALL user interviews to produce
        a competency radar and top weak topics.
        Uses selectinload — no N+1 queries.
        """
        interviews = await get_interviews_by_user(db, user_id)

        dim_sums: Dict[str, float] = {
            "correctness": 0.0, "optimality": 0.0,
            "complexity": 0.0, "explanation": 0.0, "gaps": 0.0,
        }
        dim_count = 0
        all_weak: List[str] = []

        for interview in interviews:
            stmt = (
                select(Question)
                .where(Question.interview_id == interview.id)
                .options(
                    selectinload(Question.answers).selectinload(Answer.evaluations)
                )
            )
            res = await db.execute(stmt)
            questions = res.scalars().unique().all()

            for q in questions:
                if not q.answers:
                    continue
                evals = q.answers[0].evaluations
                if not evals:
                    continue
                score = evals[0].score_json
                for k in dim_sums:
                    dim_sums[k] += score.get(k, 0)
                dim_count += 1
                all_weak.extend(evals[0].weak_topics or [])

        dimensions = (
            {k: round(v / dim_count, 2) for k, v in dim_sums.items()}
            if dim_count > 0
            else {k: 0.0 for k in dim_sums}
        )

        top_weak = [t for t, _ in Counter(all_weak).most_common(5)]

        return {
            "dimensions": dimensions,
            "interviews_count": len(interviews),
            "evaluated_answers": dim_count,
            "weak_topics": top_weak,
        }

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _find_unanswered(self, db: AsyncSession,
        questions
    ) -> Optional[Any]:
        """Возвращает первый вопрос без ответа, или None."""
        for question in reversed(questions):
            answers = await get_answers_by_question(db, question.id)
            if not answers:
                return question
        return None

    async def _collect_weak_topics(self, db: AsyncSession,
       questions
    ) -> List[str]:
        """Собирает слабые темы из всех предыдущих оценок."""
        weak_topics: List[str] = []
        for question in questions:
            answers = await get_answers_by_question(db, question.id)
            if answers:
                evaluations = await get_evaluations_by_answer(db, answers[0].id)
                if evaluations:
                    weak_topics.extend(evaluations[0].weak_topics or [])
        return weak_topics
