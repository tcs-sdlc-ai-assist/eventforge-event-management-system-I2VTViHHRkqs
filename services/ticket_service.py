import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.ticket import Ticket
from models.ticket_type import TicketType
from models.event import Event
from models.user import User


class TicketService:

    @staticmethod
    async def claim_ticket(
        db: AsyncSession,
        user: User,
        event_id: int,
        ticket_type_id: int,
        quantity: int = 1,
    ) -> Ticket:
        event_result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if event is None:
            raise ValueError("Event not found")

        now = datetime.now(timezone.utc)
        if event.end_datetime < now:
            raise ValueError("This event has already ended")

        tt_result = await db.execute(
            select(TicketType).where(
                TicketType.id == ticket_type_id,
                TicketType.event_id == event_id,
            )
        )
        ticket_type = tt_result.scalar_one_or_none()
        if ticket_type is None:
            raise ValueError("Ticket type not found for this event")

        sold_result = await db.execute(
            select(func.coalesce(func.sum(Ticket.quantity), 0)).where(
                Ticket.event_id == event_id,
                Ticket.ticket_type_id == ticket_type_id,
                Ticket.status == "confirmed",
            )
        )
        sold_count = sold_result.scalar()

        available = ticket_type.quantity - sold_count
        if quantity > available:
            raise ValueError(
                f"Not enough tickets available. Only {available} left."
            )

        total_sold_result = await db.execute(
            select(func.coalesce(func.sum(Ticket.quantity), 0)).where(
                Ticket.event_id == event_id,
                Ticket.status == "confirmed",
            )
        )
        total_sold = total_sold_result.scalar()

        if total_sold + quantity > event.total_capacity:
            raise ValueError("Event capacity has been reached")

        ticket = Ticket(
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            attendee_id=user.id,
            quantity=quantity,
            status="confirmed",
            checked_in=False,
            created_at=now,
            updated_at=now,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def check_in_attendee(
        db: AsyncSession,
        organizer: User,
        event_id: int,
        attendee_id: int,
    ) -> Ticket:
        event_result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if event is None:
            raise ValueError("Event not found")

        if organizer.role not in ("admin", "organizer"):
            raise PermissionError("Only organizers and admins can check in attendees")

        if organizer.role == "organizer" and event.organizer_id != organizer.id:
            raise PermissionError("You are not the organizer of this event")

        ticket_result = await db.execute(
            select(Ticket)
            .where(
                Ticket.event_id == event_id,
                Ticket.attendee_id == attendee_id,
                Ticket.status == "confirmed",
            )
            .options(
                selectinload(Ticket.event),
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.attendee),
            )
        )
        ticket = ticket_result.scalar_one_or_none()
        if ticket is None:
            raise ValueError("No confirmed ticket found for this attendee at this event")

        if ticket.checked_in:
            raise ValueError("Attendee is already checked in")

        ticket.checked_in = True
        ticket.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def get_tickets_for_event(
        db: AsyncSession,
        event_id: int,
    ) -> list[Ticket]:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.event_id == event_id, Ticket.status == "confirmed")
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.attendee),
                selectinload(Ticket.event),
            )
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_tickets_for_user(
        db: AsyncSession,
        user_id: int,
    ) -> list[Ticket]:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.attendee_id == user_id)
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.event),
                selectinload(Ticket.attendee),
            )
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_user_tickets_for_event(
        db: AsyncSession,
        user_id: int,
        event_id: int,
    ) -> list[Ticket]:
        result = await db.execute(
            select(Ticket)
            .where(
                Ticket.attendee_id == user_id,
                Ticket.event_id == event_id,
            )
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.event),
                selectinload(Ticket.attendee),
            )
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_ticket_sold_counts(
        db: AsyncSession,
        event_id: int,
    ) -> dict[int, int]:
        result = await db.execute(
            select(
                Ticket.ticket_type_id,
                func.coalesce(func.sum(Ticket.quantity), 0),
            )
            .where(
                Ticket.event_id == event_id,
                Ticket.status == "confirmed",
            )
            .group_by(Ticket.ticket_type_id)
        )
        rows = result.all()
        return {int(row[0]): int(row[1]) for row in rows}

    @staticmethod
    async def get_event_attendee_count(
        db: AsyncSession,
        event_id: int,
    ) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(Ticket.quantity), 0)).where(
                Ticket.event_id == event_id,
                Ticket.status == "confirmed",
            )
        )
        return int(result.scalar())

    @staticmethod
    async def get_event_checked_in_count(
        db: AsyncSession,
        event_id: int,
    ) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(Ticket.quantity), 0)).where(
                Ticket.event_id == event_id,
                Ticket.status == "confirmed",
                Ticket.checked_in == True,
            )
        )
        return int(result.scalar())

    @staticmethod
    async def get_event_revenue(
        db: AsyncSession,
        event_id: int,
    ) -> int:
        result = await db.execute(
            select(
                func.coalesce(
                    func.sum(Ticket.quantity * TicketType.price), 0
                )
            )
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .where(
                Ticket.event_id == event_id,
                Ticket.status == "confirmed",
            )
        )
        return int(result.scalar())