from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnswerBase(BaseModel):
    text: Optional[str] = None
    code: Optional[str] = None


class AnswerCreate(AnswerBase):
    question_id: int


class AnswerUpdate(AnswerBase):
    pass


class Answer(AnswerBase):
    id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True
