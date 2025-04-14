# app/models/stations.py
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.bookings import Booking  # Import the Booking model
from app.models.admin import admin_stations  # Import the Booking model

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    charging_type = Column(String)
    power_output = Column(Float)
    is_available = Column(Boolean, default=True)
    is_maintenance = Column(Boolean, default=False)
    
    # Add relationship with admins
    admins = relationship("Admin", secondary=admin_stations, back_populates="stations")
    bookings = relationship("Booking", back_populates="station")
