# app/models/stations.py
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.bookings import Booking  # Import the Booking model
from app.models.user import User  # Import the Booking model

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    charging_type = Column(String)  # AC, DC, Fast Charging
    power_output = Column(Float)  # in kW
    is_available = Column(Boolean, default=True)
    
    # Relationships
    bookings = relationship("Booking", back_populates="station")
    
    def is_within_radius(self, lat, lon, radius):
        from app.utils.distance_calculator import haversine_distance
        return haversine_distance(self.latitude, self.longitude, lat, lon) <= radius