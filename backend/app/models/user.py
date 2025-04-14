from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    phone_number = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)


    bookings = relationship("Booking", back_populates="user")