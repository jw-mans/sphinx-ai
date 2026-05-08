"""
Feedback endpoints for collecting NPS, CSAT, and CES scores.

NPS  (Net Promoter Score)  — 0-10 scale
CSAT (Customer Satisfaction) — 1-5 scale
CES  (Customer Effort Score) — 1-7 scale  (1 = very easy, 7 = very hard)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.app.metrics import nps_scores, csat_scores, ces_scores

router = APIRouter(prefix="/feedback", tags=["feedback"])


class NPSPayload(BaseModel):
    score: int = Field(..., ge=0, le=10, description="NPS score 0-10")
    interview_id: Optional[int] = None
    comment: Optional[str] = None


class CSATPayload(BaseModel):
    score: int = Field(..., ge=1, le=5, description="CSAT score 1-5")
    interview_id: Optional[int] = None
    comment: Optional[str] = None


class CESPayload(BaseModel):
    score: int = Field(..., ge=1, le=7, description="CES score 1-7 (1=very easy)")
    interview_id: Optional[int] = None
    comment: Optional[str] = None


@router.post("/nps", status_code=200)
async def submit_nps(payload: NPSPayload):
    """
    Collect Net Promoter Score.
    Score 0-6 → Detractor, 7-8 → Passive, 9-10 → Promoter.
    """
    nps_scores.labels(score=str(payload.score)).inc()

    category = (
        "promoter" if payload.score >= 9
        else "passive" if payload.score >= 7
        else "detractor"
    )
    return {"status": "ok", "category": category}


@router.post("/csat", status_code=200)
async def submit_csat(payload: CSATPayload):
    """Collect Customer Satisfaction score (1-5)."""
    csat_scores.labels(score=str(payload.score)).inc()
    return {"status": "ok"}


@router.post("/ces", status_code=200)
async def submit_ces(payload: CESPayload):
    """Collect Customer Effort Score (1-7). Lower is better."""
    ces_scores.labels(score=str(payload.score)).inc()
    return {"status": "ok"}
