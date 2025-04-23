# app/models/stations.py
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.bookings import Booking  # Import the Booking model
from app.models.admin import admin_stations  # Import the Booking model

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    name = Column(String, index=True)
    location = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True)
    is_maintenance = Column(Boolean, default=False)
    
    # Add relationship with admins
    admins = relationship("Admin", secondary=admin_stations, back_populates="stations")
    bookings = relationship("Booking", back_populates="station")
    charging_configs = relationship("ChargingConfig", back_populates="station", lazy="joined")

