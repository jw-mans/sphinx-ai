from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    telegram_id: str


class UserUpdate(BaseModel):
    telegram_id: Optional[str] = None


class User(BaseModel):
    id: int
    telegram_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
