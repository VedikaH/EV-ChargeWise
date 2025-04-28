from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.bookings import Booking
from app.models.stations import Station
from app.models.payments import Payment
from app.schemas.bookings import BookingCreate, PaymentRequest
from app.models.admin import Admin
from app.models.user import User
from app.services.payment_services import PayPalService
from app.services.payment_tasks import check_payment_status, expire_pending_payment
from app.core.config import settings
from app.models.chargingCosts import ChargingConfig


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
            Booking.status.in_(["pending", "confirmed", "paid"]),  # Only consider active bookings
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).all()
        
        return len(conflicting_bookings) == 0

    def validate_admin_access(self, station_id: int) -> bool:
        """Validate if the admin has access to the station"""
        if not self.current_admin:
            return True  # Skip validation if not admin
            
        station = self.db.query(Station).filter(Station.id == station_id).first()
        if not station or station not in self.current_admin.stations:
            return False
        return True
    
    def calculate_total_cost(self, station_id: int, start_time: datetime, end_time: datetime) -> float:
        # Get charging config for the station
        charging_config = self.db.query(ChargingConfig).filter(ChargingConfig.station_id == station_id).first()
        
        if not charging_config:
            raise ValueError("Charging configuration not found for this station")

        # Calculate the duration of the booking in hours
        duration_hours = (end_time - start_time).total_seconds() / 3600  # Convert seconds to hours
        
        # Get power output and cost per kWh
        power_output_kw = charging_config.power_output  # in kW
        cost_per_kwh = charging_config.cost_per_kwh  # in your currency

        # Calculate the total energy consumed
        energy_consumed_kwh = power_output_kw * duration_hours

        # Calculate the total cost
        total_cost = energy_consumed_kwh * cost_per_kwh
        return total_cost


    def create_booking(self, booking_data: BookingCreate, user_id: int) -> Dict[str, Any]:
        """
        Create a booking and initiate payment process
        
        :param booking_data: Booking details
        :param user_id: ID of the user making the booking
        :return: Dictionary containing booking and payment details
        """
        # Validate station exists and is available
        station = self.db.query(Station).filter(Station.id == booking_data.station_id).first()
        if not station:
            raise ValueError("Station not found")
        
        # Validate admin access if applicable
        if not self.validate_admin_access(booking_data.station_id):
            raise ValueError("Not authorized to book this station")
        
        # Check station availability for the time slot
        if not self.check_station_availability(
            booking_data.station_id, 
            booking_data.start_time, 
            booking_data.end_time
        ):
            raise ValueError("Selected time slot is not available")
        
        total_cost = self.calculate_total_cost(
        booking_data.station_id, 
        booking_data.start_time, 
        booking_data.end_time
        )
        
        # Create booking
        new_booking = Booking(
            user_id=user_id,
            station_id=booking_data.station_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            total_cost=total_cost,
            status='pending'
        )
        
        self.db.add(new_booking)
        self.db.flush()  # Get ID without committing
        
        # Create payment record
        paypal_service = PayPalService()
        
        try:
            # Create PayPal order
            order_result = paypal_service.create_order(
                amount=booking_data.total_cost,
                currency="USD",
                invoice_id=str(new_booking.id)
            )
            
            # Extract order ID and approval link
            order_id = order_result.get('id')
            approval_link = next(
                (link['href'] for link in order_result.get('links', []) 
                 if link['rel'] == 'payer-action'),
                None
            )
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                booking_id=new_booking.id,
                order_id=order_id,
                amount=booking_data.total_cost,
                currency="USD",
                status="created"
            )
            
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(new_booking)
            self.db.refresh(payment)
            
            # Schedule payment status check and expiration tasks
            check_payment_status.apply_async(
                args=[payment.id, order_id],
                countdown=60  # Check after 1 minute
            )
            
            expire_pending_payment.apply_async(
                args=[payment.id, new_booking.id],
                countdown=settings.PAYMENT_TIMEOUT_MINUTES * 60  # Convert to seconds
            )
            
            return {
                "booking": new_booking,
                "payment": {
                    "id": payment.id,
                    "order_id": order_id,
                    "approval_link": approval_link,
                    "status": payment.status
                }
            }
            
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to create payment: {str(e)}")

    def cancel_booking(self, booking_id: int, user_id: Optional[int] = None) -> Booking:
        """
        Cancel an existing booking
        
        :param booking_id: ID of the booking to cancel
        :param user_id: Optional user ID to validate ownership
        :return: Updated booking object
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise ValueError("Booking not found")
        
        # Check if user is authorized to cancel this booking
        if user_id and booking.user_id != user_id:
            raise ValueError("Not authorized to cancel this booking")
        
        # Check if booking is already paid - need special handling
        if booking.status == "paid":
            # We need to process a refund instead of simple cancellation
            raise ValueError("Cannot cancel a paid booking. Please request a refund instead.")
        
        # Update booking status
        booking.status = 'cancelled'
        
        # Cancel associated payment if exists
        if booking.payment:
            booking.payment.status = "cancelled"
        
        self.db.commit()
        self.db.refresh(booking)
        
        return booking
        
    def get_booking_payment_status(self, booking_id: int) -> Dict[str, Any]:
        """
        Get payment status for a booking
        
        :param booking_id: ID of the booking
        :return: Dictionary with payment status details
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise ValueError("Booking not found")
            
        result = {
            "booking_id": booking.id,
            "booking_status": booking.status,
            "payment_status": None,
            "payment_details": None
        }
        
        # Get associated payment if exists
        if booking.payment:
            result["payment_status"] = booking.payment.status
            result["payment_details"] = {
                "payment_id": booking.payment.id,
                "order_id": booking.payment.order_id,
                "amount": booking.payment.amount,
                "currency": booking.payment.currency,
                "created_at": booking.payment.created_at,
                "updated_at": booking.payment.updated_at
            }
            
            # If payment is still pending, trigger a status check
            if booking.payment.status in ["created", "pending", "PENDING"]:
                check_payment_status.delay(booking.payment.id, booking.payment.order_id)
        
        return result