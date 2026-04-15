import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.event import Event
from models.event_category import EventCategory
from models.ticket_type import TicketType
from models.ticket import Ticket
from models.rsvp import RSVP
from utils.security import hash_password, create_access_token


@pytest_asyncio.fixture
async def category(db_session: AsyncSession) -> EventCategory:
    cat = EventCategory(
        name="TestCategory",
        color="#FF0000",
        icon="🎯",
    )
    db_session.add(cat)
    await db_session.flush()
    await db_session.refresh(cat)
    return cat


@pytest_asyncio.fixture
async def organizer(db_session: AsyncSession) -> User:
    user = User(
        username="ticketorganizer",
        email="ticketorganizer@eventforge.com",
        display_name="Ticket Organizer",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def attendee(db_session: AsyncSession) -> User:
    user = User(
        username="ticketattendee",
        email="ticketattendee@eventforge.com",
        display_name="Ticket Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_organizer(db_session: AsyncSession) -> User:
    user = User(
        username="otherorganizer",
        email="otherorganizer@eventforge.com",
        display_name="Other Organizer",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def future_event(
    db_session: AsyncSession,
    organizer: User,
    category: EventCategory,
) -> Event:
    now = datetime.now(timezone.utc)
    event = Event(
        title="Test Ticket Event",
        description="An event for testing tickets and RSVPs.",
        category_id=category.id,
        organizer_id=organizer.id,
        venue_name="Test Venue",
        address_line="123 Test St",
        city="TestCity",
        state="TS",
        country="Testland",
        start_datetime=now + timedelta(days=30),
        end_datetime=now + timedelta(days=30, hours=8),
        total_capacity=100,
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def ticket_type_general(
    db_session: AsyncSession,
    future_event: Event,
) -> TicketType:
    tt = TicketType(
        event_id=future_event.id,
        name="General Admission",
        price=0,
        quantity=50,
    )
    db_session.add(tt)
    await db_session.flush()
    await db_session.refresh(tt)
    return tt


@pytest_asyncio.fixture
async def ticket_type_limited(
    db_session: AsyncSession,
    future_event: Event,
) -> TicketType:
    tt = TicketType(
        event_id=future_event.id,
        name="Limited VIP",
        price=100,
        quantity=1,
    )
    db_session.add(tt)
    await db_session.flush()
    await db_session.refresh(tt)
    return tt


@pytest.mark.asyncio
async def test_claim_ticket_success(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/tickets",
        data={
            "ticket_type_id": str(ticket_type_general.id),
            "quantity": "2",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "ticket_id" in data
    assert data["message"] == "Ticket claimed successfully!"


@pytest.mark.asyncio
async def test_claim_ticket_sold_out(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
    ticket_type_limited: TicketType,
    db_session: AsyncSession,
):
    existing_ticket = Ticket(
        event_id=future_event.id,
        ticket_type_id=ticket_type_limited.id,
        attendee_id=attendee.id,
        quantity=1,
        status="confirmed",
        checked_in=False,
    )
    db_session.add(existing_ticket)
    await db_session.flush()

    second_attendee = User(
        username="secondattendee",
        email="secondattendee@eventforge.com",
        display_name="Second Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(second_attendee)
    await db_session.flush()
    await db_session.refresh(second_attendee)

    token = create_access_token(data={"sub": str(second_attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/tickets",
        data={
            "ticket_type_id": str(ticket_type_limited.id),
            "quantity": "1",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Not enough tickets available" in data["error"]


@pytest.mark.asyncio
async def test_claim_ticket_unauthenticated(
    client: AsyncClient,
    future_event: Event,
    ticket_type_general: TicketType,
):
    client.cookies.clear()

    response = await client.post(
        f"/events/{future_event.id}/tickets",
        data={
            "ticket_type_id": str(ticket_type_general.id),
            "quantity": "1",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rsvp_creation(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "going"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "RSVP updated!"
    assert data["rsvp"]["status"] == "going"
    assert data["rsvp"]["event_id"] == future_event.id
    assert data["rsvp"]["user_id"] == attendee.id
    assert data["counts"]["going"] == 1
    assert data["counts"]["maybe"] == 0
    assert data["counts"]["not_going"] == 0


@pytest.mark.asyncio
async def test_rsvp_uniqueness_upsert(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response1 = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "going"},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["rsvp"]["status"] == "going"
    rsvp_id = data1["rsvp"]["id"]

    response2 = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "maybe"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["rsvp"]["status"] == "maybe"
    assert data2["rsvp"]["id"] == rsvp_id

    assert data2["counts"]["going"] == 0
    assert data2["counts"]["maybe"] == 1


@pytest.mark.asyncio
async def test_rsvp_status_change(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response1 = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "going"},
    )
    assert response1.status_code == 200
    assert response1.json()["rsvp"]["status"] == "going"

    response2 = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "not_going"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["rsvp"]["status"] == "not_going"
    assert data2["counts"]["going"] == 0
    assert data2["counts"]["not_going"] == 1

    response3 = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "maybe"},
    )
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["rsvp"]["status"] == "maybe"
    assert data3["counts"]["maybe"] == 1
    assert data3["counts"]["going"] == 0
    assert data3["counts"]["not_going"] == 0


@pytest.mark.asyncio
async def test_rsvp_invalid_status(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "invalid_status"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_checkin_by_organizer(
    client: AsyncClient,
    organizer: User,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
    db_session: AsyncSession,
):
    ticket = Ticket(
        event_id=future_event.id,
        ticket_type_id=ticket_type_general.id,
        attendee_id=attendee.id,
        quantity=1,
        status="confirmed",
        checked_in=False,
    )
    db_session.add(ticket)
    await db_session.flush()
    await db_session.refresh(ticket)

    token = create_access_token(data={"sub": str(organizer.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/checkin/{attendee.id}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["checked_in"] is True
    assert data["message"] == "Attendee checked in successfully!"
    assert data["ticket_id"] == ticket.id


@pytest.mark.asyncio
async def test_checkin_already_checked_in(
    client: AsyncClient,
    organizer: User,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
    db_session: AsyncSession,
):
    ticket = Ticket(
        event_id=future_event.id,
        ticket_type_id=ticket_type_general.id,
        attendee_id=attendee.id,
        quantity=1,
        status="confirmed",
        checked_in=True,
    )
    db_session.add(ticket)
    await db_session.flush()

    token = create_access_token(data={"sub": str(organizer.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/checkin/{attendee.id}",
    )

    assert response.status_code == 400
    data = response.json()
    assert "already checked in" in data["error"].lower()


@pytest.mark.asyncio
async def test_checkin_by_non_owner_organizer_forbidden(
    client: AsyncClient,
    other_organizer: User,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
    db_session: AsyncSession,
):
    ticket = Ticket(
        event_id=future_event.id,
        ticket_type_id=ticket_type_general.id,
        attendee_id=attendee.id,
        quantity=1,
        status="confirmed",
        checked_in=False,
    )
    db_session.add(ticket)
    await db_session.flush()

    token = create_access_token(data={"sub": str(other_organizer.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/checkin/{attendee.id}",
    )

    assert response.status_code == 403
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_checkin_by_attendee_forbidden(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
    db_session: AsyncSession,
):
    second_attendee = User(
        username="checkinattendee",
        email="checkinattendee@eventforge.com",
        display_name="Checkin Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(second_attendee)
    await db_session.flush()
    await db_session.refresh(second_attendee)

    ticket = Ticket(
        event_id=future_event.id,
        ticket_type_id=ticket_type_general.id,
        attendee_id=second_attendee.id,
        quantity=1,
        status="confirmed",
        checked_in=False,
    )
    db_session.add(ticket)
    await db_session.flush()

    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/checkin/{second_attendee.id}",
    )

    assert response.status_code == 403
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_checkin_no_ticket_found(
    client: AsyncClient,
    organizer: User,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(organizer.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/checkin/{attendee.id}",
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_claim_ticket_invalid_ticket_type(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/tickets",
        data={
            "ticket_type_id": "99999",
            "quantity": "1",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_claim_ticket_zero_quantity(
    client: AsyncClient,
    attendee: User,
    future_event: Event,
    ticket_type_general: TicketType,
):
    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.post(
        f"/events/{future_event.id}/tickets",
        data={
            "ticket_type_id": str(ticket_type_general.id),
            "quantity": "0",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_rsvp_unauthenticated(
    client: AsyncClient,
    future_event: Event,
):
    client.cookies.clear()

    response = await client.post(
        f"/events/{future_event.id}/rsvp",
        data={"status": "going"},
    )

    assert response.status_code == 401