
from app.database.base import Base
from app.schemas.bookings import PaymentRequest, PaymentResponse
from app.services.payment_services import PayPalService

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

# Payment Model
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=True)
    amount = Column(Float)
    currency = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    booking = relationship("Booking", back_populates="payment")