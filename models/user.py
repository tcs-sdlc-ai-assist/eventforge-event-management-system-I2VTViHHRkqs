import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Integer, String, event
from sqlalchemy.orm import relationship

from database import Base


class UserRole(str, PyEnum):
    admin = "admin"
    organizer = "organizer"
    attendee = "attendee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.attendee.value)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organized_events = relationship(
        "Event",
        back_populates="organizer",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tickets = relationship(
        "Ticket",
        back_populates="attendee",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    rsvps = relationship(
        "RSVP",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(timezone.utc)