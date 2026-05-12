from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.core.llm_client import LLMClient
from src.app.core.llm_client_new import LLMClientNew
from src.app.core.security import decode_token
from src.app.services import InterviewService

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    """
    Returns the authenticated user_id or raises HTTP 401.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id


def get_llm_client() -> LLMClient:
    return LLMClient()


def get_interview_service(llm_client: LLMClient = Depends(get_llm_client)) -> InterviewService:
    return InterviewService(llm_client)


def get_llm_client_new() -> LLMClientNew:
    return LLMClientNew()


def get_interview_service_v2(llm_client: LLMClientNew = Depends(get_llm_client_new)) -> InterviewService:
    return InterviewService(llm_client)