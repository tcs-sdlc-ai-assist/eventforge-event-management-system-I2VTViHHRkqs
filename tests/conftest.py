import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base
from models.user import User
from models.event_category import EventCategory
from models.event import Event
from models.ticket_type import TicketType
from models.ticket import Ticket
from models.rsvp import RSVP
from utils.security import hash_password, create_access_token


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from main import app
    from utils.dependencies import get_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="testadmin",
        email="testadmin@eventforge.com",
        display_name="Test Admin",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def organizer_user(db_session: AsyncSession) -> User:
    user = User(
        username="testorganizer",
        email="testorganizer@eventforge.com",
        display_name="Test Organizer",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def attendee_user(db_session: AsyncSession) -> User:
    user = User(
        username="testattendee",
        email="testattendee@eventforge.com",
        display_name="Test Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_categories(db_session: AsyncSession) -> list[EventCategory]:
    categories_data = [
        {"name": "Music", "color": "#8B5CF6", "icon": "🎵"},
        {"name": "Technology", "color": "#3B82F6", "icon": "💻"},
        {"name": "Sports", "color": "#10B981", "icon": "⚽"},
    ]
    categories = []
    for cat_data in categories_data:
        category = EventCategory(
            name=cat_data["name"],
            color=cat_data["color"],
            icon=cat_data["icon"],
        )
        db_session.add(category)
        await db_session.flush()
        await db_session.refresh(category)
        categories.append(category)
    return categories


@pytest_asyncio.fixture
async def admin_token(admin_user: User) -> str:
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest_asyncio.fixture
async def organizer_token(organizer_user: User) -> str:
    return create_access_token(data={"sub": str(organizer_user.id)})


@pytest_asyncio.fixture
async def attendee_token(attendee_user: User) -> str:
    return create_access_token(data={"sub": str(attendee_user.id)})


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient,
    admin_token: str,
) -> AsyncClient:
    client.cookies.set("access_token", admin_token)
    return client


@pytest_asyncio.fixture
async def organizer_client(
    client: AsyncClient,
    organizer_token: str,
) -> AsyncClient:
    client.cookies.set("access_token", organizer_token)
    return client


@pytest_asyncio.fixture
async def attendee_client(
    client: AsyncClient,
    attendee_token: str,
) -> AsyncClient:
    client.cookies.set("access_token", attendee_token)
    return client