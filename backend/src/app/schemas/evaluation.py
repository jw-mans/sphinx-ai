from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime


class EvaluationBase(BaseModel):
    score_json: Dict[str, Any]
    feedback: str
    weak_topics: Optional[List[str]] = None


class EvaluationCreate(EvaluationBase):
    answer_id: int


class EvaluationUpdate(BaseModel):
    score_json: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    weak_topics: Optional[List[str]] = None


class Evaluation(EvaluationBase):
    id: int
    answer_id: int
    created_at: datetime

    class Config:
        from_attributes = True
