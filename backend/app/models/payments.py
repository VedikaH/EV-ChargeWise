
from app.database.base import Base
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=True)
    order_id = Column(String(255), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="created")  # created, approved, captured, cancelled, refunded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payment_method = Column(String(50), default="paypal")
    transaction_id = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", back_populates="payment", uselist=False)