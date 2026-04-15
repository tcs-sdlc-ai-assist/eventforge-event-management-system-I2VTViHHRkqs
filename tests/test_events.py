import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.event import Event
from models.event_category import EventCategory
from models.ticket_type import TicketType
from models.user import User
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
        username="eventorganizer",
        email="eventorganizer@eventforge.com",
        display_name="Event Organizer",
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
        username="eventattendee",
        email="eventattendee@eventforge.com",
        display_name="Event Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin(db_session: AsyncSession) -> User:
    user = User(
        username="eventadmin",
        email="eventadmin@eventforge.com",
        display_name="Event Admin",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_event(
    db_session: AsyncSession,
    organizer: User,
    category: EventCategory,
) -> Event:
    now = datetime.now(timezone.utc)
    event = Event(
        title="Sample Test Event",
        description="A sample event for testing purposes.",
        category_id=category.id,
        organizer_id=organizer.id,
        venue_name="Test Venue",
        address_line="123 Test Street",
        city="TestCity",
        state="TS",
        country="Testland",
        start_datetime=now + timedelta(days=7),
        end_datetime=now + timedelta(days=7, hours=8),
        total_capacity=100,
    )
    db_session.add(event)
    await db_session.flush()

    tt = TicketType(
        event_id=event.id,
        name="General Admission",
        price=0,
        quantity=80,
    )
    db_session.add(tt)
    await db_session.flush()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def multiple_events(
    db_session: AsyncSession,
    organizer: User,
    category: EventCategory,
) -> list[Event]:
    now = datetime.now(timezone.utc)
    events = []
    for i in range(15):
        event = Event(
            title=f"Paginated Event {i + 1:02d}",
            description=f"Description for paginated event {i + 1}.",
            category_id=category.id,
            organizer_id=organizer.id,
            venue_name=f"Venue {i + 1}",
            address_line=f"{i + 1} Pagination Ave",
            city="PageCity" if i < 10 else "OtherCity",
            state="PG",
            country="Testland",
            start_datetime=now + timedelta(days=i + 1),
            end_datetime=now + timedelta(days=i + 1, hours=4),
            total_capacity=50 + i,
        )
        db_session.add(event)
        events.append(event)
    await db_session.flush()
    for event in events:
        await db_session.refresh(event)
    return events


def _make_token(user: User) -> str:
    return create_access_token(data={"sub": str(user.id)})


class TestCreateEvent:
    """Tests for event creation."""

    @pytest.mark.asyncio
    async def test_create_event_form_as_organizer(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        response = await client.get(
            "/events/new",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Create" in response.text or "create" in response.text

    @pytest.mark.asyncio
    async def test_create_event_submit_as_organizer(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=10, hours=6)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "New Organizer Event",
            "description": "A brand new event created by organizer.",
            "category_id": str(category.id),
            "venue_name": "Grand Hall",
            "address_line": "456 Event Blvd",
            "city": "EventCity",
            "state": "EC",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "200",
            "ticket_type_name_0": "Standard",
            "ticket_type_price_0": "25",
            "ticket_type_quantity_0": "150",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/events/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_create_event_as_attendee_forbidden(
        self,
        client: AsyncClient,
        attendee: User,
        category: EventCategory,
    ):
        token = _make_token(attendee)
        response = await client.get(
            "/events/new",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/events" in location

    @pytest.mark.asyncio
    async def test_create_event_submit_as_attendee_forbidden(
        self,
        client: AsyncClient,
        attendee: User,
        category: EventCategory,
    ):
        token = _make_token(attendee)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=10, hours=6)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Attendee Event Attempt",
            "description": "Should not be created.",
            "category_id": str(category.id),
            "venue_name": "Forbidden Venue",
            "address_line": "789 Nope St",
            "city": "NoCity",
            "state": "",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "100",
            "ticket_type_name_0": "Basic",
            "ticket_type_price_0": "0",
            "ticket_type_quantity_0": "100",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/events" in location

    @pytest.mark.asyncio
    async def test_create_event_unauthenticated(
        self,
        client: AsyncClient,
    ):
        response = await client.get(
            "/events/new",
            follow_redirects=False,
        )
        # Should get 401 or redirect
        assert response.status_code in (401, 302, 303, 422)

    @pytest.mark.asyncio
    async def test_create_event_as_admin(
        self,
        client: AsyncClient,
        admin: User,
        category: EventCategory,
    ):
        token = _make_token(admin)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=15, hours=4)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Admin Created Event",
            "description": "Event created by admin user.",
            "category_id": str(category.id),
            "venue_name": "Admin Hall",
            "address_line": "1 Admin Way",
            "city": "AdminCity",
            "state": "AD",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "300",
            "ticket_type_name_0": "Free",
            "ticket_type_price_0": "0",
            "ticket_type_quantity_0": "300",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/events/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_create_event_validation_errors(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)

        form_data = {
            "title": "",
            "description": "",
            "category_id": "0",
            "venue_name": "",
            "address_line": "",
            "city": "",
            "state": "",
            "country": "",
            "start_datetime": "",
            "end_datetime": "",
            "total_capacity": "0",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
        )
        assert response.status_code == 400
        assert "required" in response.text.lower() or "error" in response.text.lower()

    @pytest.mark.asyncio
    async def test_create_event_end_before_start(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=10, hours=6)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Bad Dates Event",
            "description": "End before start.",
            "category_id": str(category.id),
            "venue_name": "Time Warp Venue",
            "address_line": "1 Backwards Lane",
            "city": "TimeCity",
            "state": "",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "50",
            "ticket_type_name_0": "Basic",
            "ticket_type_price_0": "0",
            "ticket_type_quantity_0": "50",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_event_ticket_quantity_exceeds_capacity(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=10, hours=6)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Overcapacity Event",
            "description": "Ticket sum exceeds capacity.",
            "category_id": str(category.id),
            "venue_name": "Overflow Venue",
            "address_line": "999 Overflow St",
            "city": "OverCity",
            "state": "",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "50",
            "ticket_type_name_0": "Type A",
            "ticket_type_price_0": "10",
            "ticket_type_quantity_0": "30",
            "ticket_type_name_1": "Type B",
            "ticket_type_price_1": "20",
            "ticket_type_quantity_1": "30",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
        )
        assert response.status_code == 400
        assert "capacity" in response.text.lower() or "exceeds" in response.text.lower()


class TestEditEvent:
    """Tests for event editing with ownership checks."""

    @pytest.mark.asyncio
    async def test_edit_event_form_as_owner(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        response = await client.get(
            f"/events/{sample_event.id}/edit",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_edit_event_submit_as_owner(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=20, hours=5)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Updated Event Title",
            "description": "Updated description for the event.",
            "category_id": str(category.id),
            "venue_name": "Updated Venue",
            "address_line": "456 Updated St",
            "city": "UpdatedCity",
            "state": "UP",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "150",
            "ticket_type_name_0": "Updated Ticket",
            "ticket_type_price_0": "10",
            "ticket_type_quantity_0": "150",
        }

        response = await client.post(
            f"/events/{sample_event.id}/edit",
            data=form_data,
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert f"/events/{sample_event.id}" in location

    @pytest.mark.asyncio
    async def test_edit_event_as_different_organizer_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_event: Event,
    ):
        other_organizer = User(
            username="otherorganizer",
            email="otherorganizer@eventforge.com",
            display_name="Other Organizer",
            password_hash=hash_password("other123"),
            role="organizer",
        )
        db_session.add(other_organizer)
        await db_session.flush()
        await db_session.refresh(other_organizer)

        token = _make_token(other_organizer)
        response = await client.get(
            f"/events/{sample_event.id}/edit",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert f"/events/{sample_event.id}" in location

    @pytest.mark.asyncio
    async def test_edit_event_as_admin_allowed(
        self,
        client: AsyncClient,
        admin: User,
        sample_event: Event,
    ):
        token = _make_token(admin)
        response = await client.get(
            f"/events/{sample_event.id}/edit",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_edit_event_as_attendee_forbidden(
        self,
        client: AsyncClient,
        attendee: User,
        sample_event: Event,
    ):
        token = _make_token(attendee)
        response = await client.get(
            f"/events/{sample_event.id}/edit",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

    @pytest.mark.asyncio
    async def test_edit_nonexistent_event(
        self,
        client: AsyncClient,
        organizer: User,
    ):
        token = _make_token(organizer)
        response = await client.get(
            "/events/99999/edit",
            cookies={"access_token": token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_event_validation_errors(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
        category: EventCategory,
    ):
        token = _make_token(organizer)

        form_data = {
            "title": "",
            "description": "Valid description.",
            "category_id": str(category.id),
            "venue_name": "Valid Venue",
            "address_line": "Valid Address",
            "city": "ValidCity",
            "state": "",
            "country": "Testland",
            "start_datetime": "",
            "end_datetime": "",
            "total_capacity": "100",
        }

        response = await client.post(
            f"/events/{sample_event.id}/edit",
            data=form_data,
            cookies={"access_token": token},
        )
        assert response.status_code == 400


class TestDeleteEvent:
    """Tests for event deletion."""

    @pytest.mark.asyncio
    async def test_delete_event_as_owner(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        event_id = sample_event.id

        response = await client.post(
            f"/events/{event_id}/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/events" in location

    @pytest.mark.asyncio
    async def test_delete_event_as_admin(
        self,
        client: AsyncClient,
        admin: User,
        sample_event: Event,
    ):
        token = _make_token(admin)
        event_id = sample_event.id

        response = await client.post(
            f"/events/{event_id}/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

    @pytest.mark.asyncio
    async def test_delete_event_as_different_organizer_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_event: Event,
    ):
        other_organizer = User(
            username="deleteotherorg",
            email="deleteotherorg@eventforge.com",
            display_name="Delete Other Org",
            password_hash=hash_password("other123"),
            role="organizer",
        )
        db_session.add(other_organizer)
        await db_session.flush()
        await db_session.refresh(other_organizer)

        token = _make_token(other_organizer)
        response = await client.post(
            f"/events/{sample_event.id}/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "error" in location.lower() or "Permission" in location

    @pytest.mark.asyncio
    async def test_delete_event_as_attendee_forbidden(
        self,
        client: AsyncClient,
        attendee: User,
        sample_event: Event,
    ):
        token = _make_token(attendee)
        response = await client.post(
            f"/events/{sample_event.id}/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        # Should fail with permission error or redirect
        assert response.status_code in (303, 401, 403)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_event(
        self,
        client: AsyncClient,
        organizer: User,
    ):
        token = _make_token(organizer)
        response = await client.post(
            "/events/99999/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "not+found" in location.lower() or "error" in location.lower()


class TestEventDetail:
    """Tests for event detail page rendering."""

    @pytest.mark.asyncio
    async def test_event_detail_page_renders(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(f"/events/{sample_event.id}")
        assert response.status_code == 200
        assert sample_event.title in response.text
        assert sample_event.description in response.text
        assert sample_event.venue_name in response.text
        assert sample_event.city in response.text

    @pytest.mark.asyncio
    async def test_event_detail_shows_ticket_types(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(f"/events/{sample_event.id}")
        assert response.status_code == 200
        assert "General Admission" in response.text

    @pytest.mark.asyncio
    async def test_event_detail_shows_category(
        self,
        client: AsyncClient,
        sample_event: Event,
        category: EventCategory,
    ):
        response = await client.get(f"/events/{sample_event.id}")
        assert response.status_code == 200
        assert category.name in response.text

    @pytest.mark.asyncio
    async def test_event_detail_authenticated_shows_rsvp(
        self,
        client: AsyncClient,
        attendee: User,
        sample_event: Event,
    ):
        token = _make_token(attendee)
        response = await client.get(
            f"/events/{sample_event.id}",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Going" in response.text or "going" in response.text

    @pytest.mark.asyncio
    async def test_event_detail_organizer_sees_attendees_section(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        response = await client.get(
            f"/events/{sample_event.id}",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Attendees" in response.text or "attendees" in response.text

    @pytest.mark.asyncio
    async def test_event_detail_organizer_sees_manage_section(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        response = await client.get(
            f"/events/{sample_event.id}",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Edit Event" in response.text or "Manage" in response.text

    @pytest.mark.asyncio
    async def test_event_detail_nonexistent_returns_404(
        self,
        client: AsyncClient,
    ):
        response = await client.get(
            "/events/99999",
            headers={"accept": "text/html"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_event_detail_unauthenticated_shows_login_prompt(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(f"/events/{sample_event.id}")
        assert response.status_code == 200
        assert "Sign in" in response.text or "login" in response.text.lower()


class TestEventSearch:
    """Tests for event search and filtering."""

    @pytest.mark.asyncio
    async def test_browse_events_page_renders(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/events")
        assert response.status_code == 200
        assert "Browse Events" in response.text or "events" in response.text.lower()

    @pytest.mark.asyncio
    async def test_browse_events_shows_events(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get("/events")
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_by_keyword(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"keyword": "Sample Test"},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_by_keyword_no_results(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"keyword": "NonexistentXYZ123"},
        )
        assert response.status_code == 200
        assert sample_event.title not in response.text
        assert "No events found" in response.text or "no events" in response.text.lower()

    @pytest.mark.asyncio
    async def test_search_events_by_category(
        self,
        client: AsyncClient,
        sample_event: Event,
        category: EventCategory,
    ):
        response = await client.get(
            "/events",
            params={"category_id": category.id},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_by_city(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"city": "TestCity"},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_by_city_no_results(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"city": "NonexistentCity"},
        )
        assert response.status_code == 200
        assert sample_event.title not in response.text

    @pytest.mark.asyncio
    async def test_search_events_upcoming_status(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"status": "upcoming"},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_past_status_excludes_future(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            "/events",
            params={"status": "past"},
        )
        assert response.status_code == 200
        assert sample_event.title not in response.text

    @pytest.mark.asyncio
    async def test_search_events_by_date_range(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        now = datetime.now(timezone.utc)
        date_from = now.strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=30)).strftime("%Y-%m-%d")

        response = await client.get(
            "/events",
            params={"date_from": date_from, "date_to": date_to},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_search_events_combined_filters(
        self,
        client: AsyncClient,
        sample_event: Event,
        category: EventCategory,
    ):
        response = await client.get(
            "/events",
            params={
                "keyword": "Sample",
                "category_id": category.id,
                "city": "TestCity",
                "status": "upcoming",
            },
        )
        assert response.status_code == 200
        assert sample_event.title in response.text

    @pytest.mark.asyncio
    async def test_browse_events_authenticated(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        response = await client.get(
            "/events",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert sample_event.title in response.text


class TestEventPagination:
    """Tests for event listing pagination."""

    @pytest.mark.asyncio
    async def test_pagination_first_page(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 1},
        )
        assert response.status_code == 200
        # Default page size is 12, so first page should have up to 12 events
        content = response.text
        event_count = sum(
            1 for e in multiple_events[:12] if e.title in content
        )
        assert event_count > 0

    @pytest.mark.asyncio
    async def test_pagination_second_page(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 2},
        )
        assert response.status_code == 200
        # With 15 events and page_size=12, page 2 should have remaining events
        content = response.text
        # At least some events from the second page should appear
        remaining_events = multiple_events[12:]
        if remaining_events:
            found = any(e.title in content for e in remaining_events)
            assert found

    @pytest.mark.asyncio
    async def test_pagination_shows_total_count(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 1},
        )
        assert response.status_code == 200
        assert "15" in response.text or "of 15" in response.text

    @pytest.mark.asyncio
    async def test_pagination_navigation_links(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 1},
        )
        assert response.status_code == 200
        # Should have a "Next" link since there are more pages
        assert "Next" in response.text or "page=2" in response.text

    @pytest.mark.asyncio
    async def test_pagination_invalid_page_defaults(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 0},
        )
        # page=0 should be treated as page=1 (ge=1 validation)
        assert response.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_pagination_beyond_last_page(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"page": 100},
        )
        assert response.status_code == 200
        # Should show no events or empty state
        content = response.text
        has_events = any(e.title in content for e in multiple_events)
        if not has_events:
            assert "No events found" in content or "no events" in content.lower()

    @pytest.mark.asyncio
    async def test_pagination_preserves_filters(
        self,
        client: AsyncClient,
        multiple_events: list[Event],
    ):
        response = await client.get(
            "/events",
            params={"keyword": "Paginated", "page": 1},
        )
        assert response.status_code == 200
        # Should show paginated events matching keyword
        found = any(e.title in response.text for e in multiple_events)
        assert found


class TestEventEdgeCases:
    """Tests for edge cases in event management."""

    @pytest.mark.asyncio
    async def test_create_event_with_multiple_ticket_types(
        self,
        client: AsyncClient,
        organizer: User,
        category: EventCategory,
    ):
        token = _make_token(organizer)
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")
        end_dt = (now + timedelta(days=30, hours=8)).strftime("%Y-%m-%dT%H:%M")

        form_data = {
            "title": "Multi-Ticket Event",
            "description": "Event with multiple ticket types.",
            "category_id": str(category.id),
            "venue_name": "Multi Venue",
            "address_line": "100 Multi St",
            "city": "MultiCity",
            "state": "",
            "country": "Testland",
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "total_capacity": "500",
            "ticket_type_name_0": "General",
            "ticket_type_price_0": "0",
            "ticket_type_quantity_0": "300",
            "ticket_type_name_1": "VIP",
            "ticket_type_price_1": "100",
            "ticket_type_quantity_1": "150",
            "ticket_type_name_2": "Backstage",
            "ticket_type_price_2": "250",
            "ticket_type_quantity_0": "300",
            "ticket_type_quantity_2": "50",
        }

        response = await client.post(
            "/events/new",
            data=form_data,
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/events/" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_event_detail_with_error_query_param(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            f"/events/{sample_event.id}",
            params={"error": "Something went wrong"},
        )
        assert response.status_code == 200
        assert "Something went wrong" in response.text

    @pytest.mark.asyncio
    async def test_event_detail_with_success_query_param(
        self,
        client: AsyncClient,
        sample_event: Event,
    ):
        response = await client.get(
            f"/events/{sample_event.id}",
            params={"success": "Action completed"},
        )
        assert response.status_code == 200
        assert "Action completed" in response.text

    @pytest.mark.asyncio
    async def test_event_attendees_redirect_for_non_owner(
        self,
        client: AsyncClient,
        attendee: User,
        sample_event: Event,
    ):
        token = _make_token(attendee)
        response = await client.get(
            f"/events/{sample_event.id}/attendees",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

    @pytest.mark.asyncio
    async def test_event_attendees_redirect_for_owner(
        self,
        client: AsyncClient,
        organizer: User,
        sample_event: Event,
    ):
        token = _make_token(organizer)
        response = await client.get(
            f"/events/{sample_event.id}/attendees",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        # The attendees endpoint redirects to event detail
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert f"/events/{sample_event.id}" in location