import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.rsvp import RSVP
from models.event import Event
from schemas.rsvp import RSVPCreate, RSVPResponse, RSVPCountResponse


class RSVPService:

    @staticmethod
    async def set_rsvp(
        db: AsyncSession,
        event_id: int,
        user_id: int,
        rsvp_data: RSVPCreate,
    ) -> RSVP:
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalars().first()
        if event is None:
            raise ValueError("Event not found")

        result = await db.execute(
            select(RSVP).where(
                RSVP.event_id == event_id,
                RSVP.user_id == user_id,
            )
        )
        existing_rsvp = result.scalars().first()

        if existing_rsvp is not None:
            existing_rsvp.status = rsvp_data.status.value
            from datetime import datetime, timezone
            existing_rsvp.updated_at = datetime.now(timezone.utc)
            await db.flush()
            await db.refresh(existing_rsvp)
            return existing_rsvp
        else:
            new_rsvp = RSVP(
                event_id=event_id,
                user_id=user_id,
                status=rsvp_data.status.value,
            )
            db.add(new_rsvp)
            await db.flush()
            await db.refresh(new_rsvp)
            return new_rsvp

    @staticmethod
    async def get_rsvp_counts(
        db: AsyncSession,
        event_id: int,
    ) -> RSVPCountResponse:
        result = await db.execute(
            select(RSVP.status, func.count(RSVP.id))
            .where(RSVP.event_id == event_id)
            .group_by(RSVP.status)
        )
        rows = result.all()

        counts = {
            "going": 0,
            "maybe": 0,
            "not_going": 0,
        }
        total = 0
        for status, count in rows:
            if status in counts:
                counts[status] = count
            total += count

        return RSVPCountResponse(
            going=counts["going"],
            maybe=counts["maybe"],
            not_going=counts["not_going"],
            total=total,
        )

    @staticmethod
    async def get_user_rsvp(
        db: AsyncSession,
        event_id: int,
        user_id: int,
    ) -> Optional[RSVP]:
        result = await db.execute(
            select(RSVP).where(
                RSVP.event_id == event_id,
                RSVP.user_id == user_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_rsvps(
        db: AsyncSession,
        user_id: int,
    ) -> list[RSVP]:
        result = await db.execute(
            select(RSVP)
            .where(RSVP.user_id == user_id)
            .order_by(RSVP.updated_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_rsvp(
        db: AsyncSession,
        event_id: int,
        user_id: int,
    ) -> bool:
        result = await db.execute(
            select(RSVP).where(
                RSVP.event_id == event_id,
                RSVP.user_id == user_id,
            )
        )
        rsvp = result.scalars().first()
        if rsvp is None:
            return False
        await db.delete(rsvp)
        await db.flush()
        return True