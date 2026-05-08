from fastapi import APIRouter

from .interview import router as interview_router
from .user import router as user_router
from .feedback import router as feedback_router
from .auth import router as auth_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(interview_router)
router.include_router(user_router)
router.include_router(feedback_router)

__all__ = ["router"]