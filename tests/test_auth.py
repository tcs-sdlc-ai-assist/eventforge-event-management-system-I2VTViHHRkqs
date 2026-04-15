import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_register_page_loads(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Create your account" in response.text


@pytest.mark.asyncio
async def test_register_valid_attendee(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "New Attendee",
            "email": "newattendee@example.com",
            "username": "newattendee",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/login"


@pytest.mark.asyncio
async def test_register_valid_organizer(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "New Organizer",
            "email": "neworganizer@example.com",
            "username": "neworganizer",
            "password": "password123",
            "confirm_password": "password123",
            "role": "organizer",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/login"


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    existing_user = User(
        username="duplicateuser",
        email="existing@example.com",
        display_name="Existing User",
        password_hash=hash_password("password123"),
        role="attendee",
    )
    db_session.add(existing_user)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/register",
        data={
            "display_name": "Another User",
            "email": "another@example.com",
            "username": "duplicateuser",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Username already in use" in response.text


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    existing_user = User(
        username="emailuser",
        email="duplicate@example.com",
        display_name="Email User",
        password_hash=hash_password("password123"),
        role="attendee",
    )
    db_session.add(existing_user)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/register",
        data={
            "display_name": "Another User",
            "email": "duplicate@example.com",
            "username": "anotherusername",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Email already in use" in response.text


@pytest.mark.asyncio
async def test_register_password_mismatch(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Mismatch User",
            "email": "mismatch@example.com",
            "username": "mismatchuser",
            "password": "password123",
            "confirm_password": "differentpassword",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Passwords do not match" in response.text


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Short Pass",
            "email": "shortpass@example.com",
            "username": "shortpass",
            "password": "abc",
            "confirm_password": "abc",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Password must be at least 6 characters" in response.text


@pytest.mark.asyncio
async def test_register_short_username(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Short User",
            "email": "shortuser@example.com",
            "username": "ab",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Username must be at least 3 characters" in response.text


@pytest.mark.asyncio
async def test_register_empty_display_name(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "",
            "email": "emptyname@example.com",
            "username": "emptyname",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Display name is required" in response.text


@pytest.mark.asyncio
async def test_register_invalid_role(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Invalid Role",
            "email": "invalidrole@example.com",
            "username": "invalidrole",
            "password": "password123",
            "confirm_password": "password123",
            "role": "superadmin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Role must be one of" in response.text


@pytest.mark.asyncio
async def test_login_page_loads(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Welcome back" in response.text


@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient, db_session: AsyncSession):
    user = User(
        username="loginuser",
        email="loginuser@example.com",
        display_name="Login User",
        password_hash=hash_password("password123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/login",
        data={
            "username": "loginuser",
            "password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_username(client: AsyncClient):
    response = await client.post(
        "/login",
        data={
            "username": "nonexistentuser",
            "password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    user = User(
        username="wrongpassuser",
        email="wrongpass@example.com",
        display_name="Wrong Pass User",
        password_hash=hash_password("correctpassword"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/login",
        data={
            "username": "wrongpassuser",
            "password": "wrongpassword",
        },
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_empty_fields(client: AsyncClient):
    response = await client.post(
        "/login",
        data={
            "username": "",
            "password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Username and password are required" in response.text


@pytest.mark.asyncio
async def test_login_redirect_admin(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        username="adminlogin",
        email="adminlogin@example.com",
        display_name="Admin Login",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/login",
        data={
            "username": "adminlogin",
            "password": "admin123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/admin/dashboard"


@pytest.mark.asyncio
async def test_login_redirect_organizer(client: AsyncClient, db_session: AsyncSession):
    organizer = User(
        username="orglogin",
        email="orglogin@example.com",
        display_name="Organizer Login",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db_session.add(organizer)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/login",
        data={
            "username": "orglogin",
            "password": "organizer123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/organizer/dashboard"


@pytest.mark.asyncio
async def test_login_redirect_attendee(client: AsyncClient, db_session: AsyncSession):
    attendee = User(
        username="attlogin",
        email="attlogin@example.com",
        display_name="Attendee Login",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(attendee)
    await db_session.flush()
    await db_session.commit()

    response = await client.post(
        "/login",
        data={
            "username": "attlogin",
            "password": "attendee123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/attendee/dashboard"


@pytest.mark.asyncio
async def test_logout_post_clears_cookie(client: AsyncClient, db_session: AsyncSession):
    user = User(
        username="logoutuser",
        email="logoutuser@example.com",
        display_name="Logout User",
        password_hash=hash_password("password123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()

    login_response = await client.post(
        "/login",
        data={
            "username": "logoutuser",
            "password": "password123",
        },
        follow_redirects=False,
    )
    assert "access_token" in login_response.cookies

    logout_response = await client.post("/logout", follow_redirects=False)
    assert logout_response.status_code == 302
    assert logout_response.headers.get("location") == "/login"

    set_cookie_header = logout_response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header


@pytest.mark.asyncio
async def test_logout_get_clears_cookie(client: AsyncClient):
    token = create_access_token(data={"sub": "999"})
    client.cookies.set("access_token", token)

    response = await client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/login"

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_admin(
    client: AsyncClient, db_session: AsyncSession
):
    admin = User(
        username="authadmin",
        email="authadmin@example.com",
        display_name="Auth Admin",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.commit()

    token = create_access_token(data={"sub": str(admin.id)})
    client.cookies.set("access_token", token)

    response = await client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/admin/dashboard"


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_organizer(
    client: AsyncClient, db_session: AsyncSession
):
    organizer = User(
        username="authorg",
        email="authorg@example.com",
        display_name="Auth Organizer",
        password_hash=hash_password("organizer123"),
        role="organizer",
    )
    db_session.add(organizer)
    await db_session.flush()
    await db_session.commit()

    token = create_access_token(data={"sub": str(organizer.id)})
    client.cookies.set("access_token", token)

    response = await client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/organizer/dashboard"


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_attendee(
    client: AsyncClient, db_session: AsyncSession
):
    attendee = User(
        username="authatt",
        email="authatt@example.com",
        display_name="Auth Attendee",
        password_hash=hash_password("attendee123"),
        role="attendee",
    )
    db_session.add(attendee)
    await db_session.flush()
    await db_session.commit()

    token = create_access_token(data={"sub": str(attendee.id)})
    client.cookies.set("access_token", token)

    response = await client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/attendee/dashboard"


@pytest.mark.asyncio
async def test_register_page_redirects_authenticated_user(
    client: AsyncClient, db_session: AsyncSession
):
    user = User(
        username="authreg",
        email="authreg@example.com",
        display_name="Auth Reg User",
        password_hash=hash_password("password123"),
        role="attendee",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()

    token = create_access_token(data={"sub": str(user.id)})
    client.cookies.set("access_token", token)

    response = await client.get("/register", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/events"


@pytest.mark.asyncio
async def test_register_then_login_flow(client: AsyncClient):
    reg_response = await client.post(
        "/register",
        data={
            "display_name": "Flow User",
            "email": "flowuser@example.com",
            "username": "flowuser",
            "password": "flowpass123",
            "confirm_password": "flowpass123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert reg_response.status_code == 302
    assert reg_response.headers.get("location") == "/login"

    login_response = await client.post(
        "/login",
        data={
            "username": "flowuser",
            "password": "flowpass123",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert "access_token" in login_response.cookies
    assert login_response.headers.get("location") == "/attendee/dashboard"


@pytest.mark.asyncio
async def test_register_username_with_special_chars(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Special User",
            "email": "special@example.com",
            "username": "user@name!",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "Username must contain only letters, numbers, hyphens, or underscores" in response.text


@pytest.mark.asyncio
async def test_register_valid_username_with_hyphens_underscores(client: AsyncClient):
    response = await client.post(
        "/register",
        data={
            "display_name": "Hyphen User",
            "email": "hyphen-user@example.com",
            "username": "hyphen-user_123",
            "password": "password123",
            "confirm_password": "password123",
            "role": "attendee",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/login"