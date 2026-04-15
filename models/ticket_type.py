import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class TicketType(Base):
    __tablename__ = "ticket_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False, default=0)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)

    event = relationship("Event", back_populates="ticket_types", lazy="selectin")
    tickets = relationship("Ticket", back_populates="ticket_type", lazy="selectin")