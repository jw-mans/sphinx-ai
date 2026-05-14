from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)  # Telegram users
    email = Column(String, unique=True, index=True, nullable=True)         # Web users
    hashed_password = Column(String, nullable=True)                        # Web users
    name = Column(String, nullable=True)                                   # display name
    preferred_stack = Column(String, nullable=True)                        # e.g. "python, javascript"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interviews = relationship("Interview", back_populates="user")
