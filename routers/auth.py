import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from utils.dependencies import get_db, get_optional_user
from utils.security import create_access_token
from services.auth_service import AuthService
from models.user import User

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/register")
async def register_page(
    request: Request,
    user: User = Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=302)
        elif user.role == "organizer":
            return RedirectResponse(url="/organizer/dashboard", status_code=302)
        else:
            return RedirectResponse(url="/events", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "user": None,
            "error": None,
            "errors": None,
            "form_data": None,
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form("attendee"),
    db: AsyncSession = Depends(get_db),
):
    form_data = {
        "display_name": display_name,
        "email": email,
        "username": username,
        "role": role,
    }
    errors = {}

    display_name = display_name.strip()
    email = email.strip().lower()
    username = username.strip().lower()
    role = role.strip().lower()

    if not display_name:
        errors["display_name"] = "Display name is required"
    elif len(display_name) < 2:
        errors["display_name"] = "Display name must be at least 2 characters"

    if not email:
        errors["email"] = "Email is required"

    if not username:
        errors["username"] = "Username is required"
    elif len(username) < 3:
        errors["username"] = "Username must be at least 3 characters"
    elif not all(c.isalnum() or c in ("_", "-") for c in username):
        errors["username"] = "Username must contain only letters, numbers, hyphens, or underscores"

    if not password:
        errors["password"] = "Password is required"
    elif len(password) < 6:
        errors["password"] = "Password must be at least 6 characters"

    if not confirm_password:
        errors["confirm_password"] = "Please confirm your password"
    elif password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"

    allowed_roles = ("admin", "organizer", "attendee")
    if role not in allowed_roles:
        errors["role"] = f"Role must be one of: {', '.join(allowed_roles)}"

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=422,
        )

    auth_service = AuthService(db)

    try:
        await auth_service.register_user(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            role=role,
        )
    except ValueError as e:
        error_message = str(e)
        if "username" in error_message.lower():
            errors["username"] = error_message
        elif "email" in error_message.lower():
            errors["email"] = error_message
        else:
            errors["general"] = error_message

        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": error_message,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=400,
        )

    return RedirectResponse(url="/login", status_code=302)


@router.get("/login")
async def login_page(
    request: Request,
    user: User = Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=302)
        elif user.role == "organizer":
            return RedirectResponse(url="/organizer/dashboard", status_code=302)
        elif user.role == "attendee":
            return RedirectResponse(url="/attendee/dashboard", status_code=302)
        else:
            return RedirectResponse(url="/events", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "user": None,
            "error": None,
            "username": "",
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    username = username.strip()

    if not username or not password:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Username and password are required",
                "username": username,
            },
            status_code=400,
        )

    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(username=username, password=password)

    if user is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Invalid username or password",
                "username": username,
            },
            status_code=401,
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    if user.role == "admin":
        redirect_url = "/admin/dashboard"
    elif user.role == "organizer":
        redirect_url = "/organizer/dashboard"
    elif user.role == "attendee":
        redirect_url = "/attendee/dashboard"
    else:
        redirect_url = "/events"

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=3600,
    )
    return response


@router.post("/logout")
async def logout_post(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


@router.get("/logout")
async def logout_get(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response