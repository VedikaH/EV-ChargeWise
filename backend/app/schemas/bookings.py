from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.schemas.stations import StationBase
from app.schemas.user import UserBase

class BookingBase(BaseModel):
    station_id: int
    start_time: datetime
    end_time: datetime
    total_cost: float

class BookingCreate(BookingBase):
    user_id: int
    payment_id: Optional[str] = None

class BookingResponse(BookingBase):
    id: int
    status: str = "pending"
    station: Optional[StationBase]
    user: Optional[UserBase]

    class Config:
        from_attributes = True

class PaymentRequest(BaseModel):
    amount: int  # Amount in smallest currency unit (paisa for INR)
    currency: str = "USD"
    booking_id: Optional[int] = None

class PaymentResponse(BaseModel):
    order_id: str