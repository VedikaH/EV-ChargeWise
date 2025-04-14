from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database.session import get_db
from app.models.admin import Admin, AdminActivityLog
from app.auth.dependencies import get_current_admin, require_super_admin
from app.services.admin_services import AdminService
from app.schemas.bookings import BookingResponse
from app.schemas.stations import StationResponse
from typing import Optional
from app.schemas.admin import AdminActivityLogResponse, AdminCreate, AdminDashboardResponse, AdminResponse, AdminUpdate, StationAssignment

router = APIRouter()

@router.post("/super-admin/admin-create", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create new admin (super admin only)"""
    admin_service = AdminService(db)
    new_admin = admin_service.create_admin(admin_data, created_by=current_admin.id)
    return new_admin

@router.get("/super-admin/admins-list", response_model=List[AdminResponse])
async def list_all_admins(
    skip: int = 0,
    limit: int = 100,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """List all admins (super admin only)"""
    admins = db.query(Admin).offset(skip).limit(limit).all()
    return admins

@router.put("/super-admin/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_data: AdminUpdate,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update admin details (super admin only)"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    admin_service = AdminService(db)
    updated_admin = admin_service.update_admin(admin, admin_data)
    
    return updated_admin

@router.post("/super-admin/station/assign")
async def assign_station(
    assignment: StationAssignment,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Assign one station to one admin"""
    admin_service = AdminService(db)
    try:
        result = admin_service.assign_station(
            admin_id=assignment.admin_id,
            station_id=assignment.station_id
        )
        return {"message": "Station assigned", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/super-admin/stations/assign")
async def bulk_assign_stations(
    assignments: List[StationAssignment],
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Bulk assign stations to admins (super admin only)"""
    admin_service = AdminService(db)
    result = admin_service.bulk_assign_stations(assignments)
    return {"message": "Bulk station assignment completed", "results": result}

# Regular Admin Routes
@router.get("/admin/stations", response_model=List[StationResponse])
async def get_admin_stations(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get stations for current admin"""
    admin_service = AdminService(db)
    stations = admin_service.get_accessible_stations(current_admin)
    return stations

@router.get("/admin/bookings", response_model=List[BookingResponse])
async def get_admin_bookings(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    station_id: Optional[int] = None,
    status: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get bookings for admin's stations with filters"""
    admin_service = AdminService(db)
    bookings = admin_service.get_admin_bookings(
        current_admin,
        start_date=start_date,
        end_date=end_date,
        station_id=station_id,
        status=status
    )
    return bookings

@router.post("/admin/stations/{station_id}/maintenance")
async def set_station_maintenance(
    station_id: int,
    is_maintenance: bool,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Set station maintenance status"""
    admin_service = AdminService(db)
    result = admin_service.set_station_maintenance(
        current_admin,
        station_id,
        is_maintenance
    )
    return result

#For using this we should add activity logs before to all the above methods
# @router.get("/admin/activity-log", response_model=List[AdminActivityLogResponse])
# async def get_activity_log(
#     current_admin: Admin = Depends(get_current_admin),
#     skip: int = 0,
#     limit: int = 50,
#     db: Session = Depends(get_db)
# ):
#     """Get admin's activity log"""
#     logs = db.query(AdminActivityLog)\
#         .filter(AdminActivityLog.admin_id == current_admin.id)\
#         .order_by(AdminActivityLog.timestamp.desc())\
#         .offset(skip)\
#         .limit(limit)\
#         .all()
#     return logs

@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    admin_service = AdminService(db)
    dashboard_data = admin_service.get_dashboard_data(current_admin)
    return dashboard_data
