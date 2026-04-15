from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class RSVPStatus(str, Enum):
    going = "going"
    maybe = "maybe"
    not_going = "not_going"


class RSVPCreate(BaseModel):
    status: RSVPStatus

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().lower()
        allowed = {"going", "maybe", "not_going"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return v


class RSVPResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class RSVPCountResponse(BaseModel):
    going: int = 0
    maybe: int = 0
    not_going: int = 0
    total: int = 0


class RSVPMessageResponse(BaseModel):
    message: str
    rsvp: Optional[RSVPResponse] = None