from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InterviewBase(BaseModel):
    level: str
    stack: str
    status: Optional[str] = "active"


class InterviewCreate(InterviewBase):
    user_id: int


class InterviewUpdate(BaseModel):
    level: Optional[str] = None
    stack: Optional[str] = None
    status: Optional[str] = None


class Interview(InterviewBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
