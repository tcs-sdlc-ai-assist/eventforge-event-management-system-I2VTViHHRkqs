import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import Base
from models.event import Event
from models.event_category import EventCategory
from models.ticket import Ticket
from models.user import User
from utils.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


async def _require_admin(user: User) -> bool:
    if user.role != "admin":
        return False
    return True


@router.get("/admin/dashboard")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    total_events_result = await db.execute(select(func.count(Event.id)))
    total_events = total_events_result.scalar() or 0

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    total_tickets_result = await db.execute(
        select(func.coalesce(func.sum(Ticket.quantity), 0)).where(
            Ticket.status != "cancelled"
        )
    )
    total_tickets = int(total_tickets_result.scalar() or 0)

    active_organizers_result = await db.execute(
        select(func.count(func.distinct(Event.organizer_id)))
    )
    active_organizers = active_organizers_result.scalar() or 0

    stats = {
        "total_events": total_events,
        "total_users": total_users,
        "total_tickets": total_tickets,
        "active_organizers": active_organizers,
    }

    users_result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = list(users_result.scalars().all())

    categories_result = await db.execute(
        select(EventCategory).order_by(EventCategory.name.asc())
    )
    categories = list(categories_result.scalars().all())

    for cat in categories:
        event_count_result = await db.execute(
            select(func.count(Event.id)).where(Event.category_id == cat.id)
        )
        cat.event_count = event_count_result.scalar() or 0

    recent_events_result = await db.execute(
        select(Event)
        .options(
            selectinload(Event.organizer),
            selectinload(Event.category),
            selectinload(Event.ticket_types),
        )
        .order_by(Event.created_at.desc())
        .limit(10)
    )
    recent_events = list(recent_events_result.scalars().unique().all())

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "users": users,
            "categories": categories,
            "recent_events": recent_events,
            "now": lambda: datetime.now(timezone.utc),
        },
    )


@router.get("/admin/categories")
async def admin_categories_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/admin/categories")
async def admin_add_category(
    request: Request,
    name: str = Form(...),
    color: str = Form(...),
    icon: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    name = name.strip()
    color = color.strip()
    icon = icon.strip()

    if not name or not color or not icon:
        return RedirectResponse(
            url="/admin/dashboard?error=All+category+fields+are+required",
            status_code=303,
        )

    existing_result = await db.execute(
        select(EventCategory).where(EventCategory.name == name)
    )
    existing = existing_result.scalars().first()
    if existing is not None:
        return RedirectResponse(
            url="/admin/dashboard?error=Category+name+already+exists",
            status_code=303,
        )

    category = EventCategory(
        name=name,
        color=color,
        icon=icon,
    )
    db.add(category)
    await db.flush()

    logger.info(
        "Category created: id=%d, name='%s', by admin user_id=%d",
        category.id,
        category.name,
        user.id,
    )

    return RedirectResponse(
        url="/admin/dashboard?success=Category+created+successfully",
        status_code=303,
    )


@router.post("/admin/categories/{category_id}/edit")
async def admin_edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    color: str = Form(...),
    icon: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    name = name.strip()
    color = color.strip()
    icon = icon.strip()

    if not name or not color or not icon:
        return RedirectResponse(
            url="/admin/dashboard?error=All+category+fields+are+required",
            status_code=303,
        )

    result = await db.execute(
        select(EventCategory).where(EventCategory.id == category_id)
    )
    category = result.scalars().first()
    if category is None:
        return RedirectResponse(
            url="/admin/dashboard?error=Category+not+found",
            status_code=303,
        )

    duplicate_result = await db.execute(
        select(EventCategory).where(
            EventCategory.name == name,
            EventCategory.id != category_id,
        )
    )
    duplicate = duplicate_result.scalars().first()
    if duplicate is not None:
        return RedirectResponse(
            url="/admin/dashboard?error=Category+name+already+exists",
            status_code=303,
        )

    category.name = name
    category.color = color
    category.icon = icon
    await db.flush()

    logger.info(
        "Category updated: id=%d, name='%s', by admin user_id=%d",
        category.id,
        category.name,
        user.id,
    )

    return RedirectResponse(
        url="/admin/dashboard?success=Category+updated+successfully",
        status_code=303,
    )


@router.post("/admin/categories/{category_id}/delete")
async def admin_delete_category(
    request: Request,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    result = await db.execute(
        select(EventCategory).where(EventCategory.id == category_id)
    )
    category = result.scalars().first()
    if category is None:
        return RedirectResponse(
            url="/admin/dashboard?error=Category+not+found",
            status_code=303,
        )

    event_count_result = await db.execute(
        select(func.count(Event.id)).where(Event.category_id == category_id)
    )
    event_count = event_count_result.scalar() or 0
    if event_count > 0:
        return RedirectResponse(
            url="/admin/dashboard?error=Cannot+delete+category+with+existing+events",
            status_code=303,
        )

    category_name = category.name
    await db.delete(category)
    await db.flush()

    logger.info(
        "Category deleted: id=%d, name='%s', by admin user_id=%d",
        category_id,
        category_name,
        user.id,
    )

    return RedirectResponse(
        url="/admin/dashboard?success=Category+deleted+successfully",
        status_code=303,
    )


@router.post("/admin/users/{user_id}/delete")
async def admin_delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalars().first()
    if target_user is None:
        return RedirectResponse(
            url="/admin/dashboard?error=User+not+found",
            status_code=303,
        )

    if target_user.role == "admin":
        return RedirectResponse(
            url="/admin/dashboard?error=Cannot+delete+admin+users",
            status_code=303,
        )

    if target_user.id == user.id:
        return RedirectResponse(
            url="/admin/dashboard?error=Cannot+delete+your+own+account",
            status_code=303,
        )

    target_display_name = target_user.display_name
    await db.delete(target_user)
    await db.flush()

    logger.info(
        "User deleted: id=%d, username='%s', by admin user_id=%d",
        user_id,
        target_display_name,
        user.id,
    )

    return RedirectResponse(
        url="/admin/dashboard?success=User+deleted+successfully",
        status_code=303,
    )


@router.post("/admin/events/{event_id}/delete")
async def admin_delete_event(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/events", status_code=303)

    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalars().first()
    if event is None:
        return RedirectResponse(
            url="/admin/dashboard?error=Event+not+found",
            status_code=303,
        )

    event_title = event.title
    await db.delete(event)
    await db.flush()

    logger.info(
        "Event deleted by admin: id=%d, title='%s', by admin user_id=%d",
        event_id,
        event_title,
        user.id,
    )

    return RedirectResponse(
        url="/admin/dashboard?success=Event+deleted+successfully",
        status_code=303,
    )