import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.event import Event
from models.event_category import EventCategory
from models.ticket import Ticket
from models.ticket_type import TicketType
from models.user import User

logger = logging.getLogger(__name__)


class EventService:

    @staticmethod
    async def create_event(
        db: AsyncSession,
        user: User,
        title: str,
        description: str,
        category_id: int,
        venue_name: str,
        address_line: str,
        city: str,
        country: str,
        start_datetime: datetime,
        end_datetime: datetime,
        total_capacity: int,
        state: Optional[str] = None,
        ticket_types: Optional[List[Dict[str, Any]]] = None,
    ) -> Event:
        if user.role not in ("organizer", "admin"):
            raise PermissionError("Only organizers and admins can create events")

        if end_datetime <= start_datetime:
            raise ValueError("End datetime must be after start datetime")

        if total_capacity <= 0:
            raise ValueError("Total capacity must be greater than 0")

        category_result = await db.execute(
            select(EventCategory).where(EventCategory.id == category_id)
        )
        category = category_result.scalar_one_or_none()
        if category is None:
            raise ValueError("Invalid category")

        if ticket_types:
            total_ticket_quantity = sum(tt.get("quantity", 0) for tt in ticket_types)
            if total_ticket_quantity > total_capacity:
                raise ValueError("Sum of ticket quantities exceeds total capacity")

        event = Event(
            title=title,
            description=description,
            category_id=category_id,
            organizer_id=user.id,
            venue_name=venue_name,
            address_line=address_line,
            city=city,
            state=state,
            country=country,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            total_capacity=total_capacity,
        )
        db.add(event)
        await db.flush()

        if ticket_types:
            for tt_data in ticket_types:
                tt = TicketType(
                    event_id=event.id,
                    name=tt_data["name"],
                    price=tt_data.get("price", 0),
                    quantity=tt_data["quantity"],
                )
                db.add(tt)

        await db.flush()
        await db.refresh(event)

        logger.info(
            "Event created: id=%d, title='%s', organizer_id=%d",
            event.id,
            event.title,
            user.id,
        )
        return event

    @staticmethod
    async def edit_event(
        db: AsyncSession,
        user: User,
        event_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        venue_name: Optional[str] = None,
        address_line: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        total_capacity: Optional[int] = None,
        ticket_types: Optional[List[Dict[str, Any]]] = None,
    ) -> Event:
        result = await db.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.ticket_types))
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise LookupError("Event not found")

        if event.organizer_id != user.id and user.role != "admin":
            raise PermissionError("You do not have permission to edit this event")

        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if category_id is not None:
            category_result = await db.execute(
                select(EventCategory).where(EventCategory.id == category_id)
            )
            category = category_result.scalar_one_or_none()
            if category is None:
                raise ValueError("Invalid category")
            event.category_id = category_id
        if venue_name is not None:
            event.venue_name = venue_name
        if address_line is not None:
            event.address_line = address_line
        if city is not None:
            event.city = city
        if state is not None:
            event.state = state
        if country is not None:
            event.country = country
        if start_datetime is not None:
            event.start_datetime = start_datetime
        if end_datetime is not None:
            event.end_datetime = end_datetime
        if total_capacity is not None:
            if total_capacity <= 0:
                raise ValueError("Total capacity must be greater than 0")
            event.total_capacity = total_capacity

        effective_start = event.start_datetime
        effective_end = event.end_datetime
        if effective_end <= effective_start:
            raise ValueError("End datetime must be after start datetime")

        if ticket_types is not None:
            total_ticket_quantity = sum(tt.get("quantity", 0) for tt in ticket_types)
            if total_ticket_quantity > event.total_capacity:
                raise ValueError("Sum of ticket quantities exceeds total capacity")

            await db.execute(
                delete(TicketType).where(TicketType.event_id == event_id)
            )

            for tt_data in ticket_types:
                tt = TicketType(
                    event_id=event.id,
                    name=tt_data["name"],
                    price=tt_data.get("price", 0),
                    quantity=tt_data["quantity"],
                )
                db.add(tt)

        event.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(event)

        logger.info(
            "Event updated: id=%d, title='%s', by user_id=%d",
            event.id,
            event.title,
            user.id,
        )
        return event

    @staticmethod
    async def delete_event(
        db: AsyncSession,
        user: User,
        event_id: int,
    ) -> None:
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise LookupError("Event not found")

        if event.organizer_id != user.id and user.role != "admin":
            raise PermissionError("You do not have permission to delete this event")

        await db.delete(event)
        await db.flush()

        logger.info(
            "Event deleted: id=%d, by user_id=%d",
            event_id,
            user.id,
        )

    @staticmethod
    async def get_event(
        db: AsyncSession,
        event_id: int,
    ) -> Optional[Event]:
        result = await db.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.organizer),
                selectinload(Event.category),
                selectinload(Event.ticket_types),
                selectinload(Event.tickets),
                selectinload(Event.rsvps),
            )
        )
        event = result.scalar_one_or_none()
        return event

    @staticmethod
    async def list_events(
        db: AsyncSession,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        city: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> Tuple[List[Event], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 12
        if page_size > 100:
            page_size = 100

        query = select(Event).options(
            selectinload(Event.organizer),
            selectinload(Event.category),
            selectinload(Event.ticket_types),
        )
        count_query = select(func.count(Event.id))

        conditions = []

        if keyword:
            keyword_filter = f"%{keyword}%"
            conditions.append(
                (Event.title.ilike(keyword_filter)) | (Event.description.ilike(keyword_filter))
            )

        if category_id is not None:
            conditions.append(Event.category_id == category_id)

        if date_from is not None:
            conditions.append(Event.start_datetime >= date_from)

        if date_to is not None:
            conditions.append(Event.end_datetime <= date_to)

        if city:
            conditions.append(Event.city.ilike(f"%{city}%"))

        now = datetime.now(timezone.utc)
        if status == "upcoming":
            conditions.append(Event.start_datetime > now)
        elif status == "past":
            conditions.append(Event.end_datetime < now)

        for condition in conditions:
            query = query.where(condition)
            count_query = count_query.where(condition)

        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(Event.start_datetime.asc()).offset(offset).limit(page_size)

        result = await db.execute(query)
        events = list(result.scalars().unique().all())

        return events, total_count

    @staticmethod
    async def get_ticket_sold_counts(
        db: AsyncSession,
        event_id: int,
    ) -> Dict[int, int]:
        result = await db.execute(
            select(
                Ticket.ticket_type_id,
                func.coalesce(func.sum(Ticket.quantity), 0).label("sold"),
            )
            .where(Ticket.event_id == event_id)
            .where(Ticket.status != "cancelled")
            .group_by(Ticket.ticket_type_id)
        )
        rows = result.all()
        sold_map: Dict[int, int] = {}
        for row in rows:
            sold_map[row[0]] = int(row[1])
        return sold_map

    @staticmethod
    async def get_event_attendees(
        db: AsyncSession,
        event_id: int,
    ) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.event_id == event_id)
            .where(Ticket.status != "cancelled")
            .options(
                selectinload(Ticket.attendee),
                selectinload(Ticket.ticket_type),
            )
        )
        tickets = result.scalars().unique().all()

        attendees: List[Dict[str, Any]] = []
        for ticket in tickets:
            attendee_data: Dict[str, Any] = {
                "ticket_id": ticket.id,
                "attendee_id": ticket.attendee_id,
                "attendee_username": ticket.attendee.username if ticket.attendee else "Unknown",
                "attendee_display_name": ticket.attendee.display_name if ticket.attendee else "Unknown",
                "ticket_type_name": ticket.ticket_type.name if ticket.ticket_type else "N/A",
                "quantity": ticket.quantity,
                "status": ticket.status,
                "checked_in": ticket.checked_in,
                "created_at": ticket.created_at,
            }
            attendees.append(attendee_data)

        return attendees

    @staticmethod
    async def get_event_count_by_organizer(
        db: AsyncSession,
        organizer_id: int,
    ) -> int:
        result = await db.execute(
            select(func.count(Event.id)).where(Event.organizer_id == organizer_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_upcoming_event_count_by_organizer(
        db: AsyncSession,
        organizer_id: int,
    ) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(func.count(Event.id))
            .where(Event.organizer_id == organizer_id)
            .where(Event.start_datetime > now)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_total_attendees_by_organizer(
        db: AsyncSession,
        organizer_id: int,
    ) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(Ticket.quantity), 0))
            .join(Event, Ticket.event_id == Event.id)
            .where(Event.organizer_id == organizer_id)
            .where(Ticket.status != "cancelled")
        )
        return int(result.scalar() or 0)

    @staticmethod
    async def get_total_revenue_by_organizer(
        db: AsyncSession,
        organizer_id: int,
    ) -> int:
        result = await db.execute(
            select(
                func.coalesce(
                    func.sum(Ticket.quantity * TicketType.price), 0
                )
            )
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .join(Event, Ticket.event_id == Event.id)
            .where(Event.organizer_id == organizer_id)
            .where(Ticket.status != "cancelled")
        )
        return int(result.scalar() or 0)

    @staticmethod
    async def get_events_by_organizer(
        db: AsyncSession,
        organizer_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        count_result = await db.execute(
            select(func.count(Event.id)).where(Event.organizer_id == organizer_id)
        )
        total_count = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            select(Event)
            .where(Event.organizer_id == organizer_id)
            .options(
                selectinload(Event.organizer),
                selectinload(Event.category),
                selectinload(Event.ticket_types),
            )
            .order_by(Event.start_datetime.desc())
            .offset(offset)
            .limit(page_size)
        )
        events = list(result.scalars().unique().all())

        enriched_events: List[Dict[str, Any]] = []
        for event in events:
            attendee_count_result = await db.execute(
                select(func.coalesce(func.sum(Ticket.quantity), 0))
                .where(Ticket.event_id == event.id)
                .where(Ticket.status != "cancelled")
            )
            attendee_count = int(attendee_count_result.scalar() or 0)

            checked_in_result = await db.execute(
                select(func.coalesce(func.sum(Ticket.quantity), 0))
                .where(Ticket.event_id == event.id)
                .where(Ticket.status != "cancelled")
                .where(Ticket.checked_in == True)
            )
            checked_in_count = int(checked_in_result.scalar() or 0)

            revenue_result = await db.execute(
                select(
                    func.coalesce(
                        func.sum(Ticket.quantity * TicketType.price), 0
                    )
                )
                .join(TicketType, Ticket.ticket_type_id == TicketType.id)
                .where(Ticket.event_id == event.id)
                .where(Ticket.status != "cancelled")
            )
            revenue = int(revenue_result.scalar() or 0)

            event.attendee_count = attendee_count
            event.checked_in_count = checked_in_count
            event.revenue = revenue
            enriched_events.append(event)

        return enriched_events, total_count

    @staticmethod
    async def get_all_events_count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Event.id)))
        return result.scalar() or 0

    @staticmethod
    async def get_recent_events(
        db: AsyncSession,
        limit: int = 10,
    ) -> List[Event]:
        result = await db.execute(
            select(Event)
            .options(
                selectinload(Event.organizer),
                selectinload(Event.category),
                selectinload(Event.ticket_types),
            )
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    @staticmethod
    async def get_events_with_registered_count(
        db: AsyncSession,
        events: List[Event],
    ) -> List[Event]:
        for event in events:
            result = await db.execute(
                select(func.coalesce(func.sum(Ticket.quantity), 0))
                .where(Ticket.event_id == event.id)
                .where(Ticket.status != "cancelled")
            )
            event.registered_count = int(result.scalar() or 0)

            if event.category:
                event.category_name = event.category.name
                event.category_color = event.category.color
            else:
                event.category_name = None
                event.category_color = None

        return events