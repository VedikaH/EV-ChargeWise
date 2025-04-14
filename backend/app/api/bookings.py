from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union

from app.database.session import get_db
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate, BookingResponse
from app.services.booking_services import BookingService
from app.models.admin import Admin
from app.auth.dependencies import get_current_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.post("/create-booking", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ensure only authenticated users can book
):
    # Validate station exists
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Check station availability
    booking_service = BookingService(db)
    
    try:
        new_booking = booking_service.create_booking(booking, user_id=current_user.id)  # Pass user_id
        return new_booking
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/get-booking", response_model=List[BookingResponse])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ensure only the logged-in user can access their bookings
):
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    return bookings


@router.get("/booking-details/{booking_id}", response_model=BookingResponse)
def get_booking_details(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Authenticated user or admin
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Allow access only if the user owns the booking or is an admin
    if isinstance(current_user, User) and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    
    return booking

@router.get("/admin/stations/{station_id}/bookings", response_model=List[BookingResponse])
def get_station_bookings(
    station_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get bookings for a specific station (admin only)"""
    # Check if admin manages this station
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station or station not in current_admin.stations:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this station's bookings"
        )
    
    bookings = db.query(Booking).filter(Booking.station_id == station_id).all()
    return bookings