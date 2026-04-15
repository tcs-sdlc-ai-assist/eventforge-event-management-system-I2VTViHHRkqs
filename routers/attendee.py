import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.ticket_service import TicketService
from services.rsvp_service import RSVPService
from utils.dependencies import get_db, get_current_user

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/attendee/dashboard")
async def attendee_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("attendee",):
        return RedirectResponse(url="/events", status_code=303)

    tickets = await TicketService.get_tickets_for_user(db, user.id)
    rsvps = await RSVPService.get_user_rsvps(db, user.id)

    now = datetime.now(timezone.utc)

    upcoming_tickets = []
    past_tickets = []

    for ticket in tickets:
        ticket_data = ticket
        if ticket.ticket_type:
            ticket_data.ticket_type_name = ticket.ticket_type.name
        else:
            ticket_data.ticket_type_name = None

        if ticket.event:
            ticket_data.event_title = ticket.event.title
            if ticket.event.end_datetime and ticket.event.end_datetime > now:
                upcoming_tickets.append(ticket_data)
            else:
                past_tickets.append(ticket_data)
        else:
            past_tickets.append(ticket_data)

    rsvp_list = []
    for rsvp in rsvps:
        rsvp_item = rsvp
        if rsvp.event:
            rsvp_item.event_title = rsvp.event.title
        else:
            rsvp_item.event_title = None
        rsvp_list.append(rsvp_item)

    return templates.TemplateResponse(
        request,
        "attendee/my_tickets.html",
        context={
            "user": user,
            "upcoming_tickets": upcoming_tickets,
            "past_tickets": past_tickets,
            "rsvps": rsvp_list,
        },
    )


@router.get("/attendee/tickets")
async def attendee_tickets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("attendee",):
        return RedirectResponse(url="/events", status_code=303)

    tickets = await TicketService.get_tickets_for_user(db, user.id)
    rsvps = await RSVPService.get_user_rsvps(db, user.id)

    now = datetime.now(timezone.utc)

    upcoming_tickets = []
    past_tickets = []

    for ticket in tickets:
        ticket_data = ticket
        if ticket.ticket_type:
            ticket_data.ticket_type_name = ticket.ticket_type.name
        else:
            ticket_data.ticket_type_name = None

        if ticket.event:
            ticket_data.event_title = ticket.event.title
            if ticket.event.end_datetime and ticket.event.end_datetime > now:
                upcoming_tickets.append(ticket_data)
            else:
                past_tickets.append(ticket_data)
        else:
            past_tickets.append(ticket_data)

    rsvp_list = []
    for rsvp in rsvps:
        rsvp_item = rsvp
        if rsvp.event:
            rsvp_item.event_title = rsvp.event.title
        else:
            rsvp_item.event_title = None
        rsvp_list.append(rsvp_item)

    return templates.TemplateResponse(
        request,
        "attendee/my_tickets.html",
        context={
            "user": user,
            "upcoming_tickets": upcoming_tickets,
            "past_tickets": past_tickets,
            "rsvps": rsvp_list,
        },
    )