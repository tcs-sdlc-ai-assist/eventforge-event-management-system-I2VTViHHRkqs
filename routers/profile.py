import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/profile")
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
        },
    )


@router.post("/profile")
async def update_profile(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    display_name = display_name.strip()
    email = email.strip().lower()

    if not display_name:
        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "error": "Display name is required.",
            },
        )

    if len(display_name) < 2:
        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "error": "Display name must be at least 2 characters.",
            },
        )

    if not email:
        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "error": "Email is required.",
            },
        )

    if "@" not in email or "." not in email:
        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "error": "Please enter a valid email address.",
            },
        )

    if email != user.email:
        existing_email_result = await db.execute(
            select(User).where(User.email == email, User.id != user.id)
        )
        existing_email_user = existing_email_result.scalars().first()
        if existing_email_user is not None:
            return templates.TemplateResponse(
                request,
                "profile/index.html",
                context={
                    "user": user,
                    "error": "Email is already in use by another account.",
                },
            )

    user.display_name = display_name
    user.email = email

    await db.flush()
    await db.refresh(user)

    logger.info(
        "Profile updated: user_id=%d, display_name='%s', email='%s'",
        user.id,
        user.display_name,
        user.email,
    )

    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
            "success": "Profile updated successfully.",
        },
    )