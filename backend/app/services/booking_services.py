from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate
from app.models.admin import Admin


class BookingService:
    def __init__(self, db: Session, current_admin: Optional[Admin] = None):
        self.db = db
        self.current_admin = current_admin


    def check_station_availability(self, station_id: int, start_time: datetime, end_time: datetime) -> bool:
        """
        Check if the station is available for the requested time slot
        
        :param station_id: ID of the charging station
        :param start_time: Booking start time
        :param end_time: Booking end time
        :return: Boolean indicating station availability
        """
        conflicting_bookings = self.db.query(Booking).filter(
            Booking.station_id == station_id,
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).all()
        
        return len(conflicting_bookings) == 0

    def create_booking(self, booking_data: BookingCreate) -> Booking:
        # Validate station exists and is available
        station = self.db.query(Station).filter(Station.id == booking_data.station_id).first()
        if not station:
            raise ValueError("Station not found")
        
        # Validate admin access if applicable
        self.validate_admin_access(booking_data.station_id)
        
        # Check station availability for the time slot
        if not self.check_station_availability(
            booking_data.station_id, 
            booking_data.start_time, 
            booking_data.end_time
        ):
            raise ValueError("Selected time slot is not available")
        
        # Create booking
        new_booking = Booking(
            user_id=booking_data.user_id,
            station_id=booking_data.station_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            total_cost=booking_data.total_cost,
            status='pending'
        )
        
        self.db.add(new_booking)
        self.db.commit()
        self.db.refresh(new_booking)
        
        return new_booking

    def cancel_booking(self, booking_id: int):
        """
        Cancel an existing booking
        
        :param booking_id: ID of the booking to cancel
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise ValueError("Booking not found")
        
        # Update booking status
        booking.status = 'cancelled'
        self.db.commit()
        
        return booking