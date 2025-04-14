from datetime import datetime
from typing import List, Optional
from app.auth.dependencies import get_password_hash
from fastapi import HTTPException
from requests import Session
from sqlalchemy import func
from app.models.admin import Admin, AdminActivityLog
from app.models.stations import Station
from app.schemas.admin import AdminCreate, AdminUpdate, StationAssignment
from app.auth.dependencies import get_password_hash
from app.models.bookings import Booking


class AdminService:
    def __init__(self, db: Session):
        self.db = db
    
    def validate_admin_access(self, admin: Admin, station_id: int) -> bool:
        """Check if admin has access to station"""
        if admin.is_super_admin:
            return True
            
        station = self.db.query(Station).filter(Station.id == station_id).first()
        return station in admin.stations
    
    def get_accessible_stations(self, admin: Admin):
        """Get stations accessible to admin"""
        if admin.is_super_admin:
            return self.db.query(Station).all()
        return admin.stations
    
    def create_admin(self, admin_data: AdminCreate, created_by: int) -> Admin:
        """Create a new admin"""
        # Check if email already exists
        if self.db.query(Admin).filter(Admin.email == admin_data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new admin instance
        new_admin = Admin(
            username=admin_data.username,
            email=admin_data.email,
            hashed_password=get_password_hash(admin_data.password), 
            is_super_admin=admin_data.is_super_admin
        )

        # Add the new admin to the database
        self.db.add(new_admin)
        
        # # Log the activity of the current admin (who is creating this admin)
        # log = AdminActivityLog(
        #     admin_id=created_by,
        #     action="create_admin",
        #     details=f"Created new admin: {admin_data.username}"
        # )
        # self.db.add(log)
        
        # Commit the transaction
        self.db.commit()
        self.db.refresh(new_admin)  # Refresh to get the newly created admin data

        return new_admin
    
    def update_admin(self, admin: Admin, admin_data: AdminUpdate) -> Admin:
        if admin_data.username is not None:
            admin.username = admin_data.username
        if admin_data.email is not None:
            admin.email = admin_data.email
        if admin_data.is_active is not None:
            admin.is_active = admin_data.is_active
        if admin_data.is_super_admin is not None:
            admin.is_super_admin = admin_data.is_super_admin
        if admin_data.password is not None:
            admin.hashed_password = get_password_hash(admin_data.password)

        self.db.commit()
        self.db.refresh(admin)
        return admin
    
    def assign_station(self, admin_id: int, station_id: int):
        admin = self.db.query(Admin).filter(Admin.id == admin_id).first()
        station = self.db.query(Station).filter(Station.id == station_id).first()

        if not admin or not station:
            raise ValueError("Invalid admin or station ID")

        if station not in admin.stations:
            admin.stations.append(station)

        self.db.commit()
        return {"admin_id": admin_id, "station_id": station_id}

    def bulk_assign_stations(self, assignments: List[StationAssignment]):
        results = []
        for assignment in assignments:
            try:
                result = self.assign_station(
                    admin_id=assignment.admin_id,
                    station_id=assignment.station_id
                )
                results.append(result)
            except ValueError as e:
                # Optionally handle errors
                results.append({"error": str(e), "admin_id": assignment.admin_id})
        return results
    
    def get_admin_bookings(self, admin: Admin, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None, station_id: Optional[int] = None, 
                           status: Optional[str] = None):
        """Fetch bookings for admin's stations with filters"""
        
        # Get accessible stations for the admin
        accessible_stations = self.get_accessible_stations(admin)

        # Start building the query
        query = self.db.query(Booking).filter(Booking.station_id.in_([station.id for station in accessible_stations]))

        # Apply filters if provided
        if start_date:
            query = query.filter(Booking.start_time >= start_date)
        if end_date:
            query = query.filter(Booking.end_time <= end_date)
        if station_id:
            query = query.filter(Booking.station_id == station_id)
        if status:
            query = query.filter(Booking.status == status)

        # Execute the query and return the results
        bookings = query.all()
        return bookings
    def set_station_maintenance(self, admin: Admin, station_id: int, is_maintenance: bool):
        """Set the maintenance status of a station"""
        # Ensure the admin has access to the station
        station = self.db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Check if admin has access to this station (you can modify this to your access logic)
        if admin.is_super_admin or station in admin.stations:
            # Update the maintenance status
            station.is_maintenance = is_maintenance
            self.db.commit()
            self.db.refresh(station)
            return {"message": f"Station {station_id} maintenance status updated to {is_maintenance}"}
        
        raise HTTPException(status_code=403, detail="Admin does not have access to this station")

    def get_dashboard_data(self, admin: Admin):
        # Get stations accessible by admin
        stations = self.get_accessible_stations(admin)

        # Get statistics
        total_stations = len(stations)
        active_stations = len([station for station in stations if station.is_available])
        total_bookings = self.db.query(Booking).filter(Booking.station_id.in_([station.id for station in stations])).count()
        upcoming_bookings = self.db.query(Booking).filter(
            Booking.station_id.in_([station.id for station in stations]),
            Booking.start_time > datetime.utcnow()
        ).count()
        total_revenue = self.db.query(func.sum(Booking.total_cost)).filter(
            Booking.station_id.in_([station.id for station in stations])
        ).scalar()
        maintenance_stations = len([station for station in stations if station.is_maintenance])
        

        return {
            "total_stations": total_stations,
            "active_stations": active_stations,
            "total_bookings": total_bookings,
            "upcoming_bookings": upcoming_bookings,
            "total_revenue": total_revenue,
            "maintenance_stations": maintenance_stations,
        }
    
    def log_admin_activity(db: Session, admin_id: int, action: str, details: str):
        log = AdminActivityLog(
            admin_id=admin_id,
            action=action,
            details=details
        )
        db.add(log)
        db.commit()