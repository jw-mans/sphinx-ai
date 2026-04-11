from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.app.core.llm_client import LLMClient


class EvaluationService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def evaluate_answer(self, question_text: str, answer_text: str, code: str = None) -> Dict[str, Any]:
        """
        Оценивает ответ кандидата через LLM
        """
        full_answer = answer_text + (f"\n\nКод:\n{code}" if code else "")
        return await self.llm_client.evaluate_answer(question_text, full_answer)

    async def extract_weak_topics_from_feedback(self, feedback: str) -> list:
        """
        Извлекает слабые темы из фидбека
        """
        return await self.llm_client.extract_weak_topics(feedback)
