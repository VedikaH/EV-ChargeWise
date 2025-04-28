from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

# Junction table for admin-station relationship
admin_stations = Table(
    'admin_stations',
    Base.metadata,
    Column('admin_id', Integer, ForeignKey('admins.id')),
    Column('station_id', Integer, ForeignKey('stations.id')),
)

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    stations = relationship("Station", secondary="admin_stations", back_populates="admins")
    activity_logs = relationship("AdminActivityLog", back_populates="admin")

class AdminActivityLog(Base):
    __tablename__ = "admin_activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    action = Column(String)  # e.g., "station_assigned", "booking_approved"
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("Admin", back_populates="activity_logs")