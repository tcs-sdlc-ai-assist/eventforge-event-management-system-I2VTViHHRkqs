import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class EventCategory(Base):
    __tablename__ = "event_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)

    events = relationship("Event", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<EventCategory(id={self.id}, name='{self.name}')>"