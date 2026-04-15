from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class TicketTypeCreate(BaseModel):
    name: str
    price: int = 0
    quantity: int

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Ticket type name is required")
        return v.strip()

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class TicketTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    name: str
    price: int
    quantity: int
    created_at: datetime


class EventCreate(BaseModel):
    title: str
    description: str
    category_id: int
    venue_name: str
    address_line: str
    city: str
    state: Optional[str] = None
    country: str
    start_datetime: datetime
    end_datetime: datetime
    total_capacity: int
    ticket_types: list[TicketTypeCreate] = []

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title is required")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Description is required")
        return v.strip()

    @field_validator("venue_name")
    @classmethod
    def venue_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Venue name is required")
        return v.strip()

    @field_validator("address_line")
    @classmethod
    def address_line_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Address line is required")
        return v.strip()

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("City is required")
        return v.strip()

    @field_validator("country")
    @classmethod
    def country_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Country is required")
        return v.strip()

    @field_validator("total_capacity")
    @classmethod
    def capacity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Total capacity must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_event(self) -> "EventCreate":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("End datetime must be after start datetime")
        if self.ticket_types:
            total_ticket_quantity = sum(tt.quantity for tt in self.ticket_types)
            if total_ticket_quantity > self.total_capacity:
                raise ValueError("Sum of ticket quantities exceeds total capacity")
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    venue_name: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    total_capacity: Optional[int] = None
    ticket_types: Optional[list[TicketTypeCreate]] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Title cannot be empty")
            return v.strip()
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Description cannot be empty")
            return v.strip()
        return v

    @field_validator("venue_name")
    @classmethod
    def venue_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Venue name cannot be empty")
            return v.strip()
        return v

    @field_validator("address_line")
    @classmethod
    def address_line_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Address line cannot be empty")
            return v.strip()
        return v

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("City cannot be empty")
            return v.strip()
        return v

    @field_validator("country")
    @classmethod
    def country_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Country cannot be empty")
            return v.strip()
        return v

    @field_validator("total_capacity")
    @classmethod
    def capacity_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Total capacity must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_event_update(self) -> "EventUpdate":
        if self.start_datetime is not None and self.end_datetime is not None:
            if self.end_datetime <= self.start_datetime:
                raise ValueError("End datetime must be after start datetime")
        if self.ticket_types is not None and self.total_capacity is not None:
            total_ticket_quantity = sum(tt.quantity for tt in self.ticket_types)
            if total_ticket_quantity > self.total_capacity:
                raise ValueError("Sum of ticket quantities exceeds total capacity")
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category_id: int
    organizer_id: int
    venue_name: str
    address_line: str
    city: str
    state: Optional[str] = None
    country: str
    start_datetime: datetime
    end_datetime: datetime
    total_capacity: int
    created_at: datetime
    updated_at: datetime
    ticket_types: list[TicketTypeResponse] = []


class EventSearchParams(BaseModel):
    keyword: Optional[str] = None
    category_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    city: Optional[str] = None
    page: int = 1
    page_size: int = 12

    @field_validator("page")
    @classmethod
    def page_positive(cls, v: int) -> int:
        if v < 1:
            return 1
        return v

    @field_validator("page_size")
    @classmethod
    def page_size_valid(cls, v: int) -> int:
        if v < 1:
            return 12
        if v > 100:
            return 100
        return v