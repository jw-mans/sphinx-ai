from fastapi import APIRouter

from .interview import router as interview_router
from .user import router as user_router

router = APIRouter()
router.include_router(interview_router)
router.include_router(user_router)

__all__ = ["router"]