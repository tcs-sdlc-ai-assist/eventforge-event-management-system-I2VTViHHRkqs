import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.security import hash_password, verify_password


class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(
        self,
        username: str,
        email: str,
        display_name: str,
        password: str,
        role: str = "attendee",
    ) -> User:
        existing_username = await self.db.execute(
            select(User).where(User.username == username)
        )
        if existing_username.scalars().first() is not None:
            raise ValueError("Username already in use")

        existing_email = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalars().first() is not None:
            raise ValueError("Email already in use")

        password_hash = hash_password(password)

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalars().first()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()