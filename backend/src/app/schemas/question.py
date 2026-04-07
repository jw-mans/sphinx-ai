from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class QuestionBase(BaseModel):
    text: str
    topic: str
    difficulty: str


class QuestionCreate(QuestionBase):
    interview_id: int


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None


class Question(QuestionBase):
    id: int
    interview_id: int
    created_at: datetime

    class Config:
        from_attributes = True
