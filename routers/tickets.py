import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.ticket_service import TicketService
from utils.dependencies import get_db, get_current_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/events/{event_id}/tickets")
async def claim_ticket(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = request.headers.get("content-type", "")

    ticket_type_id: Optional[int] = None
    quantity: int = 1

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        ticket_type_id_raw = form.get("ticket_type_id")
        quantity_raw = form.get("quantity", "1")

        if ticket_type_id_raw is None or str(ticket_type_id_raw).strip() == "":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Please select a ticket type."},
            )

        try:
            ticket_type_id = int(ticket_type_id_raw)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid ticket type."},
            )

        try:
            quantity = int(quantity_raw)
        except (ValueError, TypeError):
            quantity = 1

        if quantity < 1:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Quantity must be at least 1."},
            )
    else:
        try:
            body = await request.json()
            ticket_type_id = body.get("ticket_type_id")
            quantity = body.get("quantity", 1)

            if ticket_type_id is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Please select a ticket type."},
                )

            ticket_type_id = int(ticket_type_id)
            quantity = int(quantity)

            if quantity < 1:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Quantity must be at least 1."},
                )
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request body."},
            )

    try:
        ticket = await TicketService.claim_ticket(
            db=db,
            user=current_user,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
        )

        logger.info(
            "Ticket claimed: ticket_id=%d, event_id=%d, user_id=%d, ticket_type_id=%d, quantity=%d",
            ticket.id,
            event_id,
            current_user.id,
            ticket_type_id,
            quantity,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "ticket_id": ticket.id,
                "message": "Ticket claimed successfully!",
            },
        )

    except ValueError as e:
        logger.warning(
            "Ticket claim failed: event_id=%d, user_id=%d, error=%s",
            event_id,
            current_user.id,
            str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.error(
            "Unexpected error claiming ticket: event_id=%d, user_id=%d, error=%s",
            event_id,
            current_user.id,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred. Please try again."},
        )


@router.post("/events/{event_id}/checkin/{attendee_id}")
async def check_in_attendee(
    request: Request,
    event_id: int,
    attendee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = await TicketService.check_in_attendee(
            db=db,
            organizer=current_user,
            event_id=event_id,
            attendee_id=attendee_id,
        )

        logger.info(
            "Attendee checked in: ticket_id=%d, event_id=%d, attendee_id=%d, by user_id=%d",
            ticket.id,
            event_id,
            attendee_id,
            current_user.id,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ticket_id": ticket.id,
                "checked_in": True,
                "message": "Attendee checked in successfully!",
            },
        )

    except PermissionError as e:
        logger.warning(
            "Check-in permission denied: event_id=%d, attendee_id=%d, user_id=%d, error=%s",
            event_id,
            attendee_id,
            current_user.id,
            str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": str(e)},
        )

    except ValueError as e:
        logger.warning(
            "Check-in failed: event_id=%d, attendee_id=%d, error=%s",
            event_id,
            attendee_id,
            str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)},
        )

    except Exception as e:
        logger.error(
            "Unexpected error during check-in: event_id=%d, attendee_id=%d, error=%s",
            event_id,
            attendee_id,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred. Please try again."},
        )


@router.get("/api/events/{event_id}/tickets")
async def get_event_tickets(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tickets = await TicketService.get_tickets_for_event(
            db=db,
            event_id=event_id,
        )

        ticket_list = []
        for ticket in tickets:
            ticket_data = {
                "id": ticket.id,
                "event_id": ticket.event_id,
                "ticket_type_id": ticket.ticket_type_id,
                "attendee_id": ticket.attendee_id,
                "quantity": ticket.quantity,
                "status": ticket.status,
                "checked_in": ticket.checked_in,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "ticket_type_name": ticket.ticket_type.name if ticket.ticket_type else None,
                "event_title": ticket.event.title if ticket.event else None,
                "attendee_username": ticket.attendee.username if ticket.attendee else None,
            }
            ticket_list.append(ticket_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"tickets": ticket_list},
        )

    except Exception as e:
        logger.error(
            "Error fetching tickets for event_id=%d: %s",
            event_id,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to fetch tickets."},
        )


@router.get("/api/users/me/tickets")
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tickets = await TicketService.get_tickets_for_user(
            db=db,
            user_id=current_user.id,
        )

        ticket_list = []
        for ticket in tickets:
            ticket_data = {
                "id": ticket.id,
                "event_id": ticket.event_id,
                "ticket_type_id": ticket.ticket_type_id,
                "attendee_id": ticket.attendee_id,
                "quantity": ticket.quantity,
                "status": ticket.status,
                "checked_in": ticket.checked_in,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "ticket_type_name": ticket.ticket_type.name if ticket.ticket_type else None,
                "event_title": ticket.event.title if ticket.event else None,
                "attendee_username": ticket.attendee.username if ticket.attendee else None,
            }
            ticket_list.append(ticket_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"tickets": ticket_list},
        )

    except Exception as e:
        logger.error(
            "Error fetching tickets for user_id=%d: %s",
            current_user.id,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to fetch tickets."},
        )