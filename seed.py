import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SessionLocal, engine, Base
from models.user import User
from models.event_category import EventCategory
from models.event import Event
from models.ticket_type import TicketType
from utils.security import hash_password


DEFAULT_CATEGORIES = [
    {"name": "Music", "color": "#8B5CF6", "icon": "🎵"},
    {"name": "Technology", "color": "#3B82F6", "icon": "💻"},
    {"name": "Sports", "color": "#10B981", "icon": "⚽"},
    {"name": "Food & Drink", "color": "#F59E0B", "icon": "🍔"},
    {"name": "Business", "color": "#6366F1", "icon": "💼"},
    {"name": "Arts", "color": "#EC4899", "icon": "🎨"},
    {"name": "Education", "color": "#14B8A6", "icon": "📚"},
    {"name": "Charity", "color": "#EF4444", "icon": "❤️"},
]

SAMPLE_EVENTS = [
    {
        "category_name": "Music",
        "title": "Summer Music Festival 2025",
        "description": "Join us for an unforgettable weekend of live music featuring top artists from around the world. Multiple stages, food vendors, and an incredible atmosphere await you at this year's biggest music event.",
        "venue_name": "Central Park Amphitheater",
        "address_line": "100 Central Park West",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "total_capacity": 500,
        "ticket_types": [
            {"name": "General Admission", "price": 50, "quantity": 350},
            {"name": "VIP", "price": 150, "quantity": 100},
            {"name": "Backstage Pass", "price": 300, "quantity": 50},
        ],
    },
    {
        "category_name": "Technology",
        "title": "Tech Innovation Summit 2025",
        "description": "Explore the latest in AI, cloud computing, and software engineering at this premier technology conference. Network with industry leaders, attend hands-on workshops, and discover cutting-edge innovations.",
        "venue_name": "Silicon Valley Convention Center",
        "address_line": "2000 Technology Drive",
        "city": "San Jose",
        "state": "CA",
        "country": "USA",
        "total_capacity": 300,
        "ticket_types": [
            {"name": "Standard", "price": 100, "quantity": 200},
            {"name": "Premium", "price": 250, "quantity": 80},
            {"name": "Speaker Pass", "price": 0, "quantity": 20},
        ],
    },
    {
        "category_name": "Sports",
        "title": "City Marathon 2025",
        "description": "Lace up your running shoes for the annual City Marathon! Whether you're a seasoned runner or a first-timer, this event offers routes for all skill levels along with cheering crowds and post-race celebrations.",
        "venue_name": "Downtown Sports Complex",
        "address_line": "500 Athletic Boulevard",
        "city": "Chicago",
        "state": "IL",
        "country": "USA",
        "total_capacity": 1000,
        "ticket_types": [
            {"name": "Full Marathon", "price": 75, "quantity": 500},
            {"name": "Half Marathon", "price": 50, "quantity": 300},
            {"name": "5K Fun Run", "price": 25, "quantity": 200},
        ],
    },
    {
        "category_name": "Food & Drink",
        "title": "International Food Festival",
        "description": "Taste your way around the world at our International Food Festival! Over 50 vendors serving cuisines from every continent, live cooking demonstrations, and a craft beverage garden.",
        "venue_name": "Waterfront Plaza",
        "address_line": "750 Harbor Drive",
        "city": "San Francisco",
        "state": "CA",
        "country": "USA",
        "total_capacity": 400,
        "ticket_types": [
            {"name": "Day Pass", "price": 30, "quantity": 300},
            {"name": "Weekend Pass", "price": 50, "quantity": 80},
            {"name": "VIP Tasting", "price": 120, "quantity": 20},
        ],
    },
    {
        "category_name": "Business",
        "title": "Startup Founders Conference",
        "description": "Connect with fellow entrepreneurs, investors, and mentors at the Startup Founders Conference. Featuring keynote speakers, pitch competitions, and networking sessions designed to accelerate your business growth.",
        "venue_name": "Grand Business Hotel",
        "address_line": "1200 Commerce Street",
        "city": "Austin",
        "state": "TX",
        "country": "USA",
        "total_capacity": 200,
        "ticket_types": [
            {"name": "Attendee", "price": 150, "quantity": 150},
            {"name": "Investor Pass", "price": 300, "quantity": 30},
            {"name": "Exhibitor", "price": 500, "quantity": 20},
        ],
    },
    {
        "category_name": "Arts",
        "title": "Contemporary Art Exhibition",
        "description": "Immerse yourself in a curated collection of contemporary art from emerging and established artists. Interactive installations, gallery talks, and a closing night gala make this a must-attend cultural event.",
        "venue_name": "Metropolitan Art Gallery",
        "address_line": "300 Museum Mile",
        "city": "Los Angeles",
        "state": "CA",
        "country": "USA",
        "total_capacity": 250,
        "ticket_types": [
            {"name": "General Entry", "price": 20, "quantity": 180},
            {"name": "Guided Tour", "price": 45, "quantity": 50},
            {"name": "Gala Night", "price": 100, "quantity": 20},
        ],
    },
    {
        "category_name": "Education",
        "title": "Future of Learning Symposium",
        "description": "Discover innovative approaches to education at this symposium bringing together educators, technologists, and policymakers. Topics include AI in education, remote learning best practices, and inclusive curriculum design.",
        "venue_name": "University Conference Hall",
        "address_line": "800 Academic Avenue",
        "city": "Boston",
        "state": "MA",
        "country": "USA",
        "total_capacity": 350,
        "ticket_types": [
            {"name": "Educator", "price": 0, "quantity": 200},
            {"name": "Professional", "price": 80, "quantity": 120},
            {"name": "Student", "price": 0, "quantity": 30},
        ],
    },
    {
        "category_name": "Charity",
        "title": "Annual Charity Gala & Auction",
        "description": "Make a difference at our Annual Charity Gala featuring a silent auction, live entertainment, gourmet dinner, and inspiring stories from the communities we serve. All proceeds support local education programs.",
        "venue_name": "Riverside Ballroom",
        "address_line": "450 Riverside Drive",
        "city": "Seattle",
        "state": "WA",
        "country": "USA",
        "total_capacity": 150,
        "ticket_types": [
            {"name": "Individual", "price": 100, "quantity": 100},
            {"name": "Couple", "price": 175, "quantity": 40},
            {"name": "Table of 10", "price": 900, "quantity": 10},
        ],
    },
]


async def seed_admin_user(db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.username == "admin")
    )
    admin = result.scalars().first()
    if admin is not None:
        print("[SEED] Admin user already exists, skipping.")
        return admin

    admin = User(
        username="admin",
        email="admin@eventforge.com",
        display_name="Admin User",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    print("[SEED] Created admin user (admin / admin123).")
    return admin


async def seed_organizer_user(db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.username == "organizer")
    )
    organizer = result.scalars().first()
    if organizer is not None:
        print("[SEED] Organizer user already exists, skipping.")
        return organizer

    organizer = User(
        username="organizer",
        email="organizer@eventforge.com",
        display_name="Demo Organizer",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db.add(organizer)
    await db.flush()
    await db.refresh(organizer)
    print("[SEED] Created organizer user (organizer / organizer123).")
    return organizer


async def seed_categories(db: AsyncSession) -> dict[str, EventCategory]:
    category_map: dict[str, EventCategory] = {}

    for cat_data in DEFAULT_CATEGORIES:
        result = await db.execute(
            select(EventCategory).where(EventCategory.name == cat_data["name"])
        )
        existing = result.scalars().first()
        if existing is not None:
            print(f"[SEED] Category '{cat_data['name']}' already exists, skipping.")
            category_map[cat_data["name"]] = existing
            continue

        category = EventCategory(
            name=cat_data["name"],
            color=cat_data["color"],
            icon=cat_data["icon"],
        )
        db.add(category)
        await db.flush()
        await db.refresh(category)
        category_map[cat_data["name"]] = category
        print(f"[SEED] Created category: {cat_data['icon']} {cat_data['name']}")

    return category_map


async def seed_events(
    db: AsyncSession,
    organizer: User,
    category_map: dict[str, EventCategory],
) -> None:
    now = datetime.now(timezone.utc)

    for idx, event_data in enumerate(SAMPLE_EVENTS):
        category_name = event_data["category_name"]
        category = category_map.get(category_name)
        if category is None:
            print(f"[SEED] Category '{category_name}' not found, skipping event '{event_data['title']}'.")
            continue

        result = await db.execute(
            select(Event).where(
                Event.title == event_data["title"],
                Event.organizer_id == organizer.id,
            )
        )
        existing = result.scalars().first()
        if existing is not None:
            print(f"[SEED] Event '{event_data['title']}' already exists, skipping.")
            continue

        start_offset = timedelta(days=7 + (idx * 14))
        start_dt = now + start_offset
        end_dt = start_dt + timedelta(hours=8)

        event = Event(
            title=event_data["title"],
            description=event_data["description"],
            category_id=category.id,
            organizer_id=organizer.id,
            venue_name=event_data["venue_name"],
            address_line=event_data["address_line"],
            city=event_data["city"],
            state=event_data.get("state"),
            country=event_data["country"],
            start_datetime=start_dt,
            end_datetime=end_dt,
            total_capacity=event_data["total_capacity"],
        )
        db.add(event)
        await db.flush()

        for tt_data in event_data.get("ticket_types", []):
            ticket_type = TicketType(
                event_id=event.id,
                name=tt_data["name"],
                price=tt_data["price"],
                quantity=tt_data["quantity"],
            )
            db.add(ticket_type)

        await db.flush()
        print(f"[SEED] Created event: '{event_data['title']}' ({category_name})")


async def run_seed() -> None:
    print("=" * 60)
    print("EventForge Database Seed Script")
    print("=" * 60)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[SEED] Database tables created/verified.")

    async with SessionLocal() as db:
        try:
            admin = await seed_admin_user(db)
            organizer = await seed_organizer_user(db)
            category_map = await seed_categories(db)
            await seed_events(db, organizer, category_map)

            await db.commit()
            print("")
            print("=" * 60)
            print("[SEED] Seeding completed successfully!")
            print("=" * 60)
            print("")
            print("Default accounts:")
            print("  Admin:     admin / admin123")
            print("  Organizer: organizer / organizer123")
            print("")
        except Exception as e:
            await db.rollback()
            print(f"[SEED] ERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())