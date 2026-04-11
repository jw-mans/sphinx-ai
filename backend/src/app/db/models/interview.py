from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.app.db.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(String, nullable=False)  # e.g., "junior", "middle", "senior"
    stack = Column(String, nullable=False)  # e.g., "python", "javascript"
    status = Column(String, default="active")  # e.g., "active", "completed"
    user_notes = Column(Text, nullable=True)   # пожелания пользователя к темам
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interviews")
    questions = relationship("Question", back_populates="interview")
