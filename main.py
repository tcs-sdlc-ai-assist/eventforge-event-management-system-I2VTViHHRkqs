import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EventForge application...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")

    try:
        from seed import run_seed
        await run_seed()
        logger.info("Database seeding completed.")
    except Exception as e:
        logger.warning("Seed script encountered an issue: %s", str(e))

    yield

    logger.info("Shutting down EventForge application...")


app = FastAPI(
    title="EventForge",
    description="A comprehensive event management platform",
    version="1.0.0",
    lifespan=lifespan,
)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


from routers.auth import router as auth_router
from routers.events import router as events_router
from routers.tickets import router as tickets_router
from routers.organizer import router as organizer_router
from routers.attendee import router as attendee_router
from routers.admin import router as admin_router
from routers.profile import router as profile_router

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(tickets_router)
app.include_router(organizer_router)
app.include_router(attendee_router)
app.include_router(admin_router)
app.include_router(profile_router)


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    from sqlalchemy.ext.asyncio import AsyncSession
    from database import SessionLocal
    from utils.dependencies import get_optional_user

    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from models.event import Event
            from models.event_category import EventCategory

            user = None
            token = request.cookies.get("access_token")
            if token:
                from utils.security import decode_access_token
                from models.user import User

                payload = decode_access_token(token)
                if payload:
                    user_id_str = payload.get("sub")
                    if user_id_str:
                        try:
                            user_id = int(user_id_str)
                            result = await db.execute(
                                select(User).where(User.id == user_id)
                            )
                            user = result.scalars().first()
                        except (ValueError, TypeError):
                            pass

            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Event)
                .where(Event.start_datetime > now)
                .options(
                    selectinload(Event.organizer),
                    selectinload(Event.category),
                    selectinload(Event.ticket_types),
                )
                .order_by(Event.start_datetime.asc())
                .limit(6)
            )
            upcoming_events = list(result.scalars().unique().all())

            from services.event_service import EventService
            upcoming_events = await EventService.get_events_with_registered_count(
                db, upcoming_events
            )

            cat_result = await db.execute(
                select(EventCategory).order_by(EventCategory.name)
            )
            categories = list(cat_result.scalars().all())

            return templates.TemplateResponse(
                request,
                "index.html",
                context={
                    "user": user,
                    "upcoming_events": upcoming_events,
                    "categories": categories,
                    "now": lambda: datetime.now(timezone.utc),
                },
            )
        except Exception as e:
            logger.exception("Error rendering home page: %s", str(e))
            return templates.TemplateResponse(
                request,
                "index.html",
                context={
                    "user": None,
                    "upcoming_events": [],
                    "categories": [],
                    "now": lambda: datetime.now(timezone.utc),
                },
            )


@app.get("/healthz")
@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Database connection failed",
            },
        )


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user = None
    token = request.cookies.get("access_token")
    if token:
        from utils.security import decode_access_token
        from models.user import User
        from database import SessionLocal
        from sqlalchemy import select

        payload = decode_access_token(token)
        if payload:
            user_id_str = payload.get("sub")
            if user_id_str:
                try:
                    user_id = int(user_id_str)
                    async with SessionLocal() as db:
                        result = await db.execute(
                            select(User).where(User.id == user_id)
                        )
                        user = result.scalars().first()
                except (ValueError, TypeError):
                    pass

    html_content = f"""
    {{% extends "base.html" %}}
    {{% block title %}}About — EventForge{{% endblock %}}
    {{% block content %}}
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 class="text-3xl font-bold text-gray-900 mb-6">About EventForge</h1>
        <p class="text-lg text-gray-600 mb-4">
            EventForge is a comprehensive event management platform built with Python and FastAPI.
            Create, discover, and manage events with ease.
        </p>
        <p class="text-lg text-gray-600 mb-4">
            Features include event creation, ticketing, RSVP management, attendee check-in,
            and organizer dashboards.
        </p>
        <a href="/events" class="inline-flex items-center px-6 py-3 rounded-lg text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors shadow-sm">
            Browse Events
        </a>
    </div>
    {{% endblock %}}
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).resolve().parent / "templates"))
    )
    template = env.from_string(
        """{% extends "base.html" %}
{% block title %}About — EventForge{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">About EventForge</h1>
    <p class="text-lg text-gray-600 mb-4">
        EventForge is a comprehensive event management platform built with Python and FastAPI.
        Create, discover, and manage events with ease.
    </p>
    <p class="text-lg text-gray-600 mb-4">
        Features include event creation, ticketing, RSVP management, attendee check-in,
        and organizer dashboards.
    </p>
    <a href="/events" class="inline-flex items-center px-6 py-3 rounded-lg text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors shadow-sm">
        Browse Events
    </a>
</div>
{% endblock %}"""
    )
    rendered = template.render(
        user=user,
        now=lambda: datetime.now(timezone.utc),
    )
    return HTMLResponse(content=rendered)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        user = None
        token = request.cookies.get("access_token")
        if token:
            from utils.security import decode_access_token
            from models.user import User
            from database import SessionLocal
            from sqlalchemy import select

            payload = decode_access_token(token)
            if payload:
                user_id_str = payload.get("sub")
                if user_id_str:
                    try:
                        user_id = int(user_id_str)
                        async with SessionLocal() as db:
                            result = await db.execute(
                                select(User).where(User.id == user_id)
                            )
                            user = result.scalars().first()
                    except (ValueError, TypeError):
                        pass

        return templates.TemplateResponse(
            request,
            "404.html",
            context={
                "user": user,
                "now": lambda: datetime.now(timezone.utc),
            },
            status_code=404,
        )
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )