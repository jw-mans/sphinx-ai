from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.core.llm_client import LLMClient
from src.app.services import InterviewService


def get_llm_client() -> LLMClient:
    return LLMClient()


def get_interview_service(llm_client: LLMClient = Depends(get_llm_client)) -> InterviewService:
    return InterviewService(llm_client)