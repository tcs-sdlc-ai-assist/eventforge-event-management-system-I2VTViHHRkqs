import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import relationship

from database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("event_categories.id"), nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    venue_name = Column(String(255), nullable=False)
    address_line = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    total_capacity = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    organizer = relationship("User", back_populates="events", lazy="selectin")
    category = relationship("EventCategory", back_populates="events", lazy="selectin")
    ticket_types = relationship("TicketType", back_populates="event", lazy="selectin", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event", lazy="selectin", cascade="all, delete-orphan")
    rsvps = relationship("RSVP", back_populates="event", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_events_title", "title"),
        Index("ix_events_city", "city"),
        Index("ix_events_start_datetime", "start_datetime"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title}', city='{self.city}')>"