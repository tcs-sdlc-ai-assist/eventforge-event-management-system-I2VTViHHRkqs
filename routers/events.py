import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.event import Event
from models.event_category import EventCategory
from services.event_service import EventService
from services.ticket_service import TicketService
from services.rsvp_service import RSVPService
from schemas.rsvp import RSVPCreate, RSVPStatus
from utils.dependencies import get_db, get_current_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/events", response_class=HTMLResponse)
async def browse_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
    keyword: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    status: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
):
    date_from_dt = None
    date_to_dt = None

    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except (ValueError, TypeError):
            date_from_dt = None

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except (ValueError, TypeError):
            date_to_dt = None

    effective_status = status if status and status != "all" else None

    page_size = 12
    events, total_count = await EventService.list_events(
        db=db,
        keyword=keyword,
        category_id=category_id,
        date_from=date_from_dt,
        date_to=date_to_dt,
        city=city,
        status=effective_status,
        page=page,
        page_size=page_size,
    )

    events = await EventService.get_events_with_registered_count(db, events)

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    cat_result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    categories = list(cat_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "events/browse.html",
        context={
            "user": user,
            "events": events,
            "categories": categories,
            "keyword": keyword or "",
            "category_id": category_id,
            "date_from": date_from or "",
            "date_to": date_to or "",
            "city": city or "",
            "status": status or "all",
            "page": page,
            "total_count": total_count,
            "total_pages": total_pages,
            "now": lambda: datetime.now(timezone.utc),
        },
    )


@router.get("/events/new", response_class=HTMLResponse)
async def new_event_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("organizer", "admin"):
        return RedirectResponse(url="/events", status_code=303)

    cat_result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    categories = list(cat_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "events/form.html",
        context={
            "user": user,
            "event": None,
            "categories": categories,
            "form_data": None,
            "errors": None,
            "now": lambda: datetime.now(timezone.utc),
        },
    )


@router.post("/events/new", response_class=HTMLResponse)
async def create_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    title: str = Form(""),
    description: str = Form(""),
    category_id: int = Form(0),
    venue_name: str = Form(""),
    address_line: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    country: str = Form(""),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    total_capacity: int = Form(0),
):
    if user.role not in ("organizer", "admin"):
        return RedirectResponse(url="/events", status_code=303)

    cat_result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    categories = list(cat_result.scalars().all())

    form_data_raw = await request.form()
    ticket_types = _extract_ticket_types(form_data_raw)

    form_data = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "venue_name": venue_name,
        "address_line": address_line,
        "city": city,
        "state": state,
        "country": country,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "total_capacity": total_capacity,
        "ticket_types": ticket_types,
    }

    errors = {}

    if not title.strip():
        errors["title"] = "Title is required"
    if not description.strip():
        errors["description"] = "Description is required"
    if category_id <= 0:
        errors["category_id"] = "Please select a category"
    if not venue_name.strip():
        errors["venue_name"] = "Venue name is required"
    if not address_line.strip():
        errors["address_line"] = "Address is required"
    if not city.strip():
        errors["city"] = "City is required"
    if not country.strip():
        errors["country"] = "Country is required"
    if total_capacity <= 0:
        errors["total_capacity"] = "Total capacity must be greater than 0"

    start_dt = None
    end_dt = None
    try:
        start_dt = datetime.fromisoformat(start_datetime)
    except (ValueError, TypeError):
        errors["start_datetime"] = "Valid start date/time is required"

    try:
        end_dt = datetime.fromisoformat(end_datetime)
    except (ValueError, TypeError):
        errors["end_datetime"] = "Valid end date/time is required"

    if start_dt and end_dt and end_dt <= start_dt:
        errors["end_datetime"] = "End date/time must be after start date/time"

    if ticket_types:
        total_ticket_qty = sum(tt.get("quantity", 0) for tt in ticket_types)
        if total_capacity > 0 and total_ticket_qty > total_capacity:
            errors["ticket_types"] = "Sum of ticket quantities exceeds total capacity"

    if errors:
        return templates.TemplateResponse(
            request,
            "events/form.html",
            context={
                "user": user,
                "event": None,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=400,
        )

    try:
        event = await EventService.create_event(
            db=db,
            user=user,
            title=title.strip(),
            description=description.strip(),
            category_id=category_id,
            venue_name=venue_name.strip(),
            address_line=address_line.strip(),
            city=city.strip(),
            country=country.strip(),
            start_datetime=start_dt,
            end_datetime=end_dt,
            total_capacity=total_capacity,
            state=state.strip() if state.strip() else None,
            ticket_types=ticket_types if ticket_types else None,
        )
        return RedirectResponse(url=f"/events/{event.id}", status_code=303)
    except (ValueError, PermissionError) as e:
        errors["general"] = str(e)
        return templates.TemplateResponse(
            request,
            "events/form.html",
            context={
                "user": user,
                "event": None,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=400,
        )


@router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    event = await EventService.get_event(db, event_id)
    if event is None:
        return templates.TemplateResponse(
            request,
            "404.html",
            context={
                "user": user,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=404,
        )

    category = event.category
    organizer = event.organizer
    ticket_types = event.ticket_types or []

    now = datetime.now(timezone.utc)
    is_past = event.end_datetime.replace(tzinfo=timezone.utc) < now if event.end_datetime.tzinfo is None else event.end_datetime < now

    ticket_sold = await EventService.get_ticket_sold_counts(db, event.id)

    rsvp_counts = await RSVPService.get_rsvp_counts(db, event.id)

    user_rsvp = None
    user_tickets = []
    if user:
        user_rsvp = await RSVPService.get_user_rsvp(db, event.id, user.id)
        raw_tickets = await TicketService.get_user_tickets_for_event(db, user.id, event.id)
        for t in raw_tickets:
            t.ticket_type_name = t.ticket_type.name if t.ticket_type else None
        user_tickets = raw_tickets

    attendees = []
    if user and (user.id == event.organizer_id or user.role == "admin"):
        attendees = await EventService.get_event_attendees(db, event.id)

    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse(
        request,
        "events/detail.html",
        context={
            "user": user,
            "event": event,
            "category": category,
            "organizer": organizer,
            "ticket_types": ticket_types,
            "ticket_sold": ticket_sold,
            "is_past": is_past,
            "rsvp_counts": rsvp_counts,
            "user_rsvp": user_rsvp,
            "user_tickets": user_tickets,
            "attendees": attendees,
            "error": error,
            "success": success,
            "now": lambda: datetime.now(timezone.utc),
        },
    )


@router.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = await EventService.get_event(db, event_id)
    if event is None:
        return templates.TemplateResponse(
            request,
            "404.html",
            context={
                "user": user,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=404,
        )

    if event.organizer_id != user.id and user.role != "admin":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    cat_result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    categories = list(cat_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "events/form.html",
        context={
            "user": user,
            "event": event,
            "categories": categories,
            "form_data": None,
            "errors": None,
            "now": lambda: datetime.now(timezone.utc),
        },
    )


@router.post("/events/{event_id}/edit", response_class=HTMLResponse)
async def update_event(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    title: str = Form(""),
    description: str = Form(""),
    category_id: int = Form(0),
    venue_name: str = Form(""),
    address_line: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    country: str = Form(""),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    total_capacity: int = Form(0),
):
    event = await EventService.get_event(db, event_id)
    if event is None:
        return templates.TemplateResponse(
            request,
            "404.html",
            context={
                "user": user,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=404,
        )

    if event.organizer_id != user.id and user.role != "admin":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    cat_result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    categories = list(cat_result.scalars().all())

    form_data_raw = await request.form()
    ticket_types = _extract_ticket_types(form_data_raw)

    form_data = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "venue_name": venue_name,
        "address_line": address_line,
        "city": city,
        "state": state,
        "country": country,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "total_capacity": total_capacity,
        "ticket_types": ticket_types,
    }

    errors = {}

    if not title.strip():
        errors["title"] = "Title is required"
    if not description.strip():
        errors["description"] = "Description is required"
    if category_id <= 0:
        errors["category_id"] = "Please select a category"
    if not venue_name.strip():
        errors["venue_name"] = "Venue name is required"
    if not address_line.strip():
        errors["address_line"] = "Address is required"
    if not city.strip():
        errors["city"] = "City is required"
    if not country.strip():
        errors["country"] = "Country is required"
    if total_capacity <= 0:
        errors["total_capacity"] = "Total capacity must be greater than 0"

    start_dt = None
    end_dt = None
    try:
        start_dt = datetime.fromisoformat(start_datetime)
    except (ValueError, TypeError):
        errors["start_datetime"] = "Valid start date/time is required"

    try:
        end_dt = datetime.fromisoformat(end_datetime)
    except (ValueError, TypeError):
        errors["end_datetime"] = "Valid end date/time is required"

    if start_dt and end_dt and end_dt <= start_dt:
        errors["end_datetime"] = "End date/time must be after start date/time"

    if ticket_types:
        total_ticket_qty = sum(tt.get("quantity", 0) for tt in ticket_types)
        if total_capacity > 0 and total_ticket_qty > total_capacity:
            errors["ticket_types"] = "Sum of ticket quantities exceeds total capacity"

    if errors:
        return templates.TemplateResponse(
            request,
            "events/form.html",
            context={
                "user": user,
                "event": event,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=400,
        )

    try:
        await EventService.edit_event(
            db=db,
            user=user,
            event_id=event_id,
            title=title.strip(),
            description=description.strip(),
            category_id=category_id,
            venue_name=venue_name.strip(),
            address_line=address_line.strip(),
            city=city.strip(),
            country=country.strip(),
            start_datetime=start_dt,
            end_datetime=end_dt,
            total_capacity=total_capacity,
            state=state.strip() if state.strip() else None,
            ticket_types=ticket_types if ticket_types else None,
        )
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)
    except (ValueError, PermissionError, LookupError) as e:
        errors["general"] = str(e)
        return templates.TemplateResponse(
            request,
            "events/form.html",
            context={
                "user": user,
                "event": event,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=400,
        )


@router.post("/events/{event_id}/delete")
async def delete_event(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await EventService.delete_event(db=db, user=user, event_id=event_id)
        return RedirectResponse(url="/events", status_code=303)
    except LookupError:
        return RedirectResponse(
            url=f"/events/{event_id}?error=Event+not+found",
            status_code=303,
        )
    except PermissionError:
        return RedirectResponse(
            url=f"/events/{event_id}?error=Permission+denied",
            status_code=303,
        )


@router.post("/events/{event_id}/rsvp")
async def set_rsvp(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str = Form(""),
):
    try:
        rsvp_data = RSVPCreate(status=status)
        rsvp = await RSVPService.set_rsvp(
            db=db,
            event_id=event_id,
            user_id=user.id,
            rsvp_data=rsvp_data,
        )
        counts = await RSVPService.get_rsvp_counts(db, event_id)
        return JSONResponse(
            content={
                "message": "RSVP updated!",
                "rsvp": {
                    "id": rsvp.id,
                    "event_id": rsvp.event_id,
                    "user_id": rsvp.user_id,
                    "status": rsvp.status,
                },
                "counts": {
                    "going": counts.going,
                    "maybe": counts.maybe,
                    "not_going": counts.not_going,
                    "total": counts.total,
                },
            }
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.exception("RSVP error for event %d, user %d", event_id, user.id)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to update RSVP."},
        )


@router.post("/events/{event_id}/tickets")
async def claim_ticket(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    ticket_type_id: int = Form(0),
    quantity: int = Form(1),
):
    try:
        ticket = await TicketService.claim_ticket(
            db=db,
            user=user,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
        )
        return JSONResponse(
            status_code=201,
            content={
                "ticket_id": ticket.id,
                "message": "Ticket claimed successfully!",
            },
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.exception(
            "Ticket claim error for event %d, user %d", event_id, user.id
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to claim ticket."},
        )


@router.post("/events/{event_id}/checkin/{attendee_id}")
async def checkin_attendee(
    request: Request,
    event_id: int,
    attendee_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        ticket = await TicketService.check_in_attendee(
            db=db,
            organizer=user,
            event_id=event_id,
            attendee_id=attendee_id,
        )
        return JSONResponse(
            content={
                "ticket_id": ticket.id,
                "checked_in": ticket.checked_in,
                "message": "Attendee checked in successfully!",
            }
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except PermissionError as e:
        return JSONResponse(
            status_code=403,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.exception(
            "Check-in error for event %d, attendee %d", event_id, attendee_id
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to check in attendee."},
        )


@router.get("/events/{event_id}/attendees", response_class=HTMLResponse)
async def event_attendees(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = await EventService.get_event(db, event_id)
    if event is None:
        return templates.TemplateResponse(
            request,
            "404.html",
            context={
                "user": user,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=404,
        )

    if event.organizer_id != user.id and user.role != "admin":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    return RedirectResponse(url=f"/events/{event_id}", status_code=303)


def _extract_ticket_types(form_data) -> list:
    ticket_types = []
    indices = set()

    for key in form_data.keys():
        if key.startswith("ticket_type_name_"):
            try:
                idx = int(key.replace("ticket_type_name_", ""))
                indices.add(idx)
            except (ValueError, TypeError):
                continue

    for idx in sorted(indices):
        name_key = f"ticket_type_name_{idx}"
        price_key = f"ticket_type_price_{idx}"
        quantity_key = f"ticket_type_quantity_{idx}"

        name = form_data.get(name_key, "").strip()
        if not name:
            continue

        try:
            price = int(form_data.get(price_key, "0"))
        except (ValueError, TypeError):
            price = 0

        try:
            quantity = int(form_data.get(quantity_key, "1"))
        except (ValueError, TypeError):
            quantity = 1

        if price < 0:
            price = 0
        if quantity < 1:
            quantity = 1

        ticket_types.append({
            "name": name,
            "price": price,
            "quantity": quantity,
        })

    return ticket_types