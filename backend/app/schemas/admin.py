from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class AdminBase(BaseModel):
    username: str
    email: str
    
    class Config:
        from_attributes = True  # Add this to all response models

class AdminCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_super_admin: bool = False  # Only settable by existing super admins

class StationAssignment(BaseModel):
    admin_id: int
    station_id: int

class AdminResponse(AdminBase):
    id: int
    
    class Config:
        from_attributes = True  # Ensure this is present

class AdminActivityLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    details: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class AdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_super_admin: Optional[bool] = None
    password: Optional[str] = None

class AdminDashboardResponse(BaseModel):
    total_stations: int
    active_stations: int
    total_bookings: int
    upcoming_bookings: int
    total_revenue: Optional[float] = None
    maintenance_stations: int
    
    class Config:
        from_attributes = True