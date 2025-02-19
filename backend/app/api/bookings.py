from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate, BookingResponse
from app.services.booking_services import BookingService


router = APIRouter()

@router.post("/", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    # Validate station exists
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Check station availability
    booking_service = BookingService(db)
    
    try:
        new_booking = booking_service.create_booking(booking)
        return new_booking
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[BookingResponse])
def get_user_bookings(
    user_id: int,
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    return bookings

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking_details(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking