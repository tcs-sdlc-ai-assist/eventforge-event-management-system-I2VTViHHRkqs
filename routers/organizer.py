import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.event_service import EventService
from utils.dependencies import get_current_user, get_db

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/organizer/dashboard")
async def organizer_dashboard(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("organizer", "admin"):
        return RedirectResponse(url="/events", status_code=303)

    if page < 1:
        page = 1

    page_size = 10

    total_events = await EventService.get_event_count_by_organizer(db, user.id)
    upcoming_events = await EventService.get_upcoming_event_count_by_organizer(db, user.id)
    total_attendees = await EventService.get_total_attendees_by_organizer(db, user.id)
    total_revenue = await EventService.get_total_revenue_by_organizer(db, user.id)

    events, total_count = await EventService.get_events_by_organizer(
        db, user.id, page=page, page_size=page_size
    )

    total_pages = max(1, math.ceil(total_count / page_size))

    if page > total_pages and total_pages > 0:
        page = total_pages

    stats = {
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "total_attendees": total_attendees,
        "total_revenue": total_revenue,
    }

    from datetime import datetime, timezone

    def _now():
        return datetime.now(timezone.utc)

    return templates.TemplateResponse(
        request,
        "organizer/dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "events": events,
            "page": page,
            "total_pages": total_pages,
            "total_events": total_count,
            "now": _now,
        },
    )