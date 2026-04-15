from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TicketClaim(BaseModel):
    ticket_type_id: int
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("ticket_type_id")
    @classmethod
    def ticket_type_id_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Invalid ticket type")
        return v


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    ticket_type_id: int
    attendee_id: int
    quantity: int
    status: str
    checked_in: bool
    created_at: datetime
    updated_at: datetime


class TicketClaimResponse(BaseModel):
    ticket_id: int
    message: str


class TicketCheckInResponse(BaseModel):
    ticket_id: int
    checked_in: bool
    message: str


class TicketListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    ticket_type_id: int
    attendee_id: int
    quantity: int
    status: str
    checked_in: bool
    created_at: datetime
    updated_at: datetime
    ticket_type_name: Optional[str] = None
    event_title: Optional[str] = None
    attendee_username: Optional[str] = None