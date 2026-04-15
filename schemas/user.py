from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


class UserCreate(BaseModel):
    display_name: str
    email: EmailStr
    username: str
    password: str
    confirm_password: str
    role: str = "attendee"

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name is required")
        if len(v) < 2:
            raise ValueError("Display name must be at least 2 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Username is required")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.isalnum() and not all(c.isalnum() or c in ("_", "-") for c in v):
            raise ValueError("Username must contain only letters, numbers, hyphens, or underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        allowed_roles = ("admin", "organizer", "attendee")
        v = v.strip().lower()
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username is required")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str
    role: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Display name cannot be empty")
            if len(v) < 2:
                raise ValueError("Display name must be at least 2 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                raise ValueError("Username cannot be empty")
            if len(v) < 3:
                raise ValueError("Username must be at least 3 characters")
            if not all(c.isalnum() or c in ("_", "-") for c in v):
                raise ValueError("Username must contain only letters, numbers, hyphens, or underscores")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed_roles = ("admin", "organizer", "attendee")
            v = v.strip().lower()
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v