from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    station_id = Column(Integer, ForeignKey('stations.id'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    total_cost = Column(Float)
    status = Column(String)
    
    user = relationship("User", back_populates="bookings")
    station = relationship("Station", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False)

