from pydantic import BaseModel, validator, Field
from datetime import datetime
from typing import Optional, Dict, Any

class BookingBase(BaseModel):
    station_id: int
    start_time: datetime
    end_time: datetime
    total_cost: float

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class BookingCreate(BookingBase):
    pass

class BookingResponse(BookingBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class PaymentRequest(BaseModel):
    booking_id: Optional[int] = None
    amount: float = Field(..., gt=0)  # Must be greater than 0
    currency: str = "USD"

class PaymentResponse(BaseModel):
    order_id: str
    approval_link: Optional[str] = None

class PaymentDetails(BaseModel):
    payment_id: int
    order_id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class BookingWithPaymentResponse(BaseModel):
    booking: BookingResponse
    payment: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True