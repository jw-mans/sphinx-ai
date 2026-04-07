from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.app.db.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)
    score_json = Column(JSON, nullable=False)  # dict with scores
    feedback = Column(Text, nullable=False)
    weak_topics = Column(JSON, nullable=True)  # list of weak topics
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("Answer", back_populates="evaluations")
