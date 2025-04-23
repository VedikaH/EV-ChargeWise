from typing import Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate
from app.models.admin import Admin
from app.models.payments import Payment
from app.services.payment_services import PayPalService


class BookingService:
    def __init__(self, db: Session, current_admin: Optional[Admin] = None):
        self.db = db
        self.current_admin = current_admin
        # Time window for payment completion (in minutes)
        self.payment_window = 15

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
            Booking.end_time > start_time,
            Booking.status.in_(['pending', 'confirmed', 'paid'])  # Exclude cancelled bookings
        ).all()
        
        return len(conflicting_bookings) == 0

    def validate_admin_access(self, station_id: int):
        """Validate admin has access to the station"""
        if self.current_admin:
            station_belongs_to_admin = any(
                station.id == station_id for station in self.current_admin.stations
            )
            if not station_belongs_to_admin:
                raise ValueError("Admin not authorized to manage this station")

    def create_booking(self, booking_data: BookingCreate, user_id: int) -> Tuple[Booking, Optional[Payment]]:
        """
        Create a new booking and initialize a payment record
        
        :param booking_data: Booking data
        :param user_id: ID of the user making the booking
        :return: Tuple of (Booking, Payment) objects
        """
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
        
        # Create booking with pending status
        new_booking = Booking(
            user_id=user_id,
            station_id=booking_data.station_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            total_cost=booking_data.total_cost,
            status='pending',
            expiration_time=datetime.now() + timedelta(minutes=self.payment_window)
        )
        
        self.db.add(new_booking)
        self.db.commit()
        self.db.refresh(new_booking)
        
        # Initialize payment record (optional at this stage)
        payment = None
        
        return new_booking, payment

    def initialize_payment(self, booking_id: int, amount: float, currency: str = 'USD') -> Payment:
        """
        Initialize a payment record for a booking
        
        :param booking_id: ID of the booking
        :param amount: Payment amount
        :param currency: Currency code
        :return: Payment object
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")
            
        if booking.status != 'pending':
            raise ValueError(f"Cannot initialize payment for booking with status '{booking.status}'")
            
        # Create payment record with pending status
        payment = Payment(
            booking_id=booking_id,
            user_id=booking.user_id,
            amount=amount,
            currency=currency,
            status='pending'
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        return payment

    def update_booking_status(self, booking_id: int, status: str) -> Booking:
        """
        Update the status of a booking
        
        :param booking_id: ID of the booking
        :param status: New status ('pending', 'confirmed', 'paid', 'cancelled')
        :return: Updated Booking object
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")
            
        booking.status = status
        
        if status == 'cancelled':
            # Optional: Free up the time slot
            pass
        elif status == 'confirmed' or status == 'paid':
            # Clear expiration time when confirmed or paid
            booking.expiration_time = None
            
        self.db.commit()
        self.db.refresh(booking)
        
        return booking

    def cancel_booking(self, booking_id: int) -> Booking:
        """
        Cancel an existing booking
        
        :param booking_id: ID of the booking to cancel
        :return: Updated Booking object
        """
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise ValueError("Booking not found")
            
        # Check if booking can be cancelled
        if booking.status == 'paid':
            raise ValueError("Cannot cancel a paid booking without processing a refund")
            
        return self.update_booking_status(booking_id, 'cancelled')
        
    def process_expired_bookings(self):
        """
        Cancel bookings that have passed their payment window
        """
        now = datetime.now()
        expired_bookings = self.db.query(Booking).filter(
            Booking.status == 'pending',
            Booking.expiration_time < now
        ).all()
        
        for booking in expired_bookings:
            self.update_booking_status(booking.id, 'cancelled')
        
        return len(expired_bookings)
    





import requests
import uuid
from typing import Dict, Any, Optional
from app.core.config import settings
from app.models.payments import Payment
from app.models.bookings import Booking
from sqlalchemy.orm import Session
from datetime import datetime

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.paypal_service = PayPalService()
        
    def create_payment_for_booking(self, booking_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a payment record and PayPal order for a booking
        
        :param booking_id: ID of the booking
        :param user_id: ID of the user making the payment
        :return: Payment details including order_id and approval_link
        """
        # Get booking details
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")
            
        # Validate booking belongs to user
        if booking.user_id != user_id:
            raise ValueError("You are not authorized to pay for this booking")
            
        # Validate booking status
        if booking.status != 'pending':
            raise ValueError(f"Cannot process payment for booking with status '{booking.status}'")
            
        # Check if booking has expired
        if booking.expiration_time and booking.expiration_time < datetime.now():
            booking.status = 'cancelled'
            self.db.commit()
            raise ValueError("Booking has expired. Please make a new booking.")
            
        # Create PayPal order
        order = self.paypal_service.create_order(
            amount=booking.total_cost,
            currency='USD',  # Assuming USD as default
            invoice_id=str(booking_id),
            items=[{
                "name": f"Charging Station Booking #{booking_id}",
                "description": f"Booking for Station #{booking.station_id}",
                "quantity": "1",
                "unit_amount": {
                    "currency_code": 'USD',
                    "value": str(booking.total_cost)
                },
                "tax": {
                    "currency_code": 'USD',
                    "value": "0.00"
                },
                "total_amount": {
                    "currency_code": 'USD',
                    "value": str(booking.total_cost)
                }
            }]
        )
        
        # Get approval link
        approval_link = next(
            (link['href'] for link in order.get('links', []) 
             if link['rel'] == 'payer-action'),
            None
        )
        
        # Store payment information
        payment = Payment(
            user_id=user_id,
            booking_id=booking_id,
            order_id=order['id'],
            amount=booking.total_cost,
            currency='USD',  # Assuming USD as default
            status='pending'
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        return {
            "payment_id": payment.id,
            "order_id": order['id'],
            "approval_link": approval_link,
            "status": "pending"
        }
        
    def verify_payment(self, order_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Verify payment status with PayPal
        
        :param order_id: PayPal order ID
        :param user_id: Optional user ID for authorization check
        :return: Payment verification details
        """
        # Get payment from database
        payment = self.db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise ValueError("Payment not found")
            
        # Optional authorization check
        if user_id is not None and payment.user_id != user_id:
            raise ValueError("You are not authorized to verify this payment")
            
        # Get payment details from PayPal
        order_details = self.paypal_service.verify_order(order_id)
        
        # Update payment status
        payment.status = order_details.get('status', payment.status)
        self.db.commit()
        
        return {
            "payment_id": payment.id,
            "order_id": order_id,
            "booking_id": payment.booking_id,
            "status": payment.status,
            "details": order_details
        }
        
    def capture_payment(self, order_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Capture an authorized payment
        
        :param order_id: PayPal order ID
        :param user_id: Optional user ID for authorization check
        :return: Payment capture details
        """
        # Get payment from database
        payment = self.db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise ValueError("Payment not found")
            
        # Optional authorization check
        if user_id is not None and payment.user_id != user_id:
            raise ValueError("You are not authorized to capture this payment")
            
        # Get booking
        booking = payment.booking if hasattr(payment, 'booking') else None
        if not booking:
            raise ValueError("Associated booking not found")
            
        # Capture payment with PayPal
        capture_result = self.paypal_service.capture_order(order_id)
        
        # Update payment status
        payment_status = capture_result.get('status', 'failed')
        payment.status = payment_status
        
        # Update booking status if payment is successful
        if payment_status == "COMPLETED":
            booking.status = "paid"
            booking.payment_id = payment.id
            booking.expiration_time = None  # Clear expiration time
        
        self.db.commit()
        
        return {
            "payment_id": payment.id,
            "order_id": order_id,
            "booking_id": booking.id,
            "status": payment_status,
            "booking_status": booking.status,
            "details": capture_result
        }


class PayPalService:
    def __init__(self):
        self.base_url = settings.PAYPAL_BASE_URL  # e.g., 'https://api-m.sandbox.paypal.com'
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        """
        Obtain OAuth 2.0 access token from PayPal
        """
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(
            url, 
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET), 
            headers=headers, 
            data=data
        )
        response.raise_for_status()
        return response.json()['access_token']

    def create_order(self, 
                 amount: float, 
                 currency: str = 'USD', 
                 invoice_id: str = None,
                 items: list = None) -> Dict[str, Any]:
        """
        Create a PayPal order
        
        :param amount: Total order amount
        :param currency: Currency code
        :param invoice_id: Optional invoice identifier
        :param items: Optional list of order items
        :return: Order creation details
        """
        url = f"{self.base_url}/v2/checkout/orders"
        
        # Default items if not provided
        if not items:
            items = [{
                "name": "Charging Station Booking",
                "description": "Booking Service",
                "quantity": "1",
                "unit_amount": {
                    "currency_code": currency,
                    "value": str(amount)
                },
                "tax": {
                    "currency_code": currency,
                    "value": "0.00"
                },
                "total_amount": {
                    "currency_code": currency,
                    "value": str(amount)
                }
            }]
        else:
            # Ensure each item has the required fields
            for item in items:
                if 'total_amount' not in item:
                    # Calculate total amount if not provided
                    quantity = float(item.get('quantity', 1))
                    unit_value = float(item['unit_amount']['value'])
                    item['total_amount'] = {
                        "currency_code": currency,
                        "value": str(quantity * unit_value)
                    }
        
        payload = {
            "intent": "CAPTURE",
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": settings.PAYPAL_RETURN_URL,
                        "cancel_url": settings.PAYPAL_CANCEL_URL
                    }
                }
            },
            "purchase_units": [{
                "invoice_id": invoice_id or str(uuid.uuid4()),
                "amount": {
                    "currency_code": currency,
                    "value": str(amount),
                    "breakdown": {
                        "item_total": {
                            "currency_code": currency,
                            "value": str(amount)
                        }
                    }
                },
                "items": items
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(uuid.uuid4()),
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def confirm_order(self, order_id: str, payment_source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm the payment source for a PayPal order
        
        :param order_id: PayPal Order ID
        :param payment_source: Payment source details
        :return: Confirmation result
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/confirm-payment-source"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "payment_source": payment_source
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Capture a previously created PayPal order
        
        :param order_id: PayPal Order ID
        :return: Capture result
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_order(self, order_id: str) -> Dict[str, Any]:
        """
        Check the status of a PayPal order
        
        :param order_id: PayPal Order ID
        :return: Order details
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    


from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    station_id = Column(Integer, ForeignKey("stations.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_cost = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, paid, cancelled
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate="CURRENT_TIMESTAMP")
    expiration_time = Column(DateTime, nullable=True)  # Time when pending booking expires
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    station = relationship("Station", back_populates="bookings")
    payment = relationship("Payment", foreign_keys=[payment_id], back_populates="booking_paid")
    payments = relationship("Payment", foreign_keys="Payment.booking_id", back_populates="booking")


from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    order_id = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, completed, failed, refunded
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", onupdate="CURRENT_TIMESTAMP")
    
    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", foreign_keys=[booking_id], back_populates="payments")
    booking_paid = relationship("Booking", foreign_keys="Booking.payment_id", back_populates="payment")


from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Union

from app.database.session import get_db
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate, BookingResponse, BookingWithPaymentResponse
from app.services.booking_services import BookingService
from app.services.payment_services import PaymentService
from app.models.admin import Admin
from app.auth.dependencies import get_current_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.post("/create-booking", response_model=BookingWithPaymentResponse)
def create_booking(
    booking: BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ensure only authenticated users can book
):
    """
    Create a new booking and initialize payment
    """
    # Validate station exists
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Create booking
    booking_service = BookingService(db)
    payment_service = PaymentService(db)
    
    try:
        # Create booking with pending status
        new_booking, _ = booking_service.create_booking(booking, user_id=current_user.id)
        
        # Initialize payment for the booking
        payment_info = payment_service.create_payment_for_booking(
            booking_id=new_booking.id,
            user_id=current_user.id
        )
        
        # Add task to cancel booking if payment not completed in time
        background_tasks.add_task(
            check_payment_status, 
            booking_id=new_booking.id, 
            order_id=payment_info["order_id"],
            db=db
        )
        
        return {
            "booking_id": new_booking.id,
            "station_id": new_booking.station_id,
            "start_time": new_booking.start_time,
            "end_time": new_booking.end_time,
            "total_cost": new_booking.total_cost,
            "status": new_booking.status,
            "expiration_time": new_booking.expiration_time,
            "payment": {
                "payment_id": payment_info["payment_id"],
                "order_id": payment_info["order_id"],
                "status": payment_info["status"],
                "approval_link": payment_info["approval_link"]
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def check_payment_status(booking_id: int, order_id: str, db: Session):
    """
    Background task to check payment status and cancel booking if expired
    """
    booking_service = BookingService(db)
    payment_service = PaymentService(db)
    
    try:
        # Check if booking is still pending and has expired
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking or booking.status != 'pending':
            return
            
        # Process expired bookings
        booking_service.process_expired_bookings()
    except Exception as e:
        # Log the error but don't fail
        print(f"Error checking payment status: {e}")


@router.get("/my-bookings", response_model=List[BookingWithPaymentResponse])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all bookings for the current user with payment info
    """
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    
    result = []
    for booking in bookings:
        # Get the most recent payment for this booking
        payment = None
        if booking.payments:
            payment = max(booking.payments, key=lambda p: p.created_at)
            
        payment_info = None
        if payment:
            payment_info = {
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "status": payment.status,
                "approval_link": None  # Can't retrieve this after creation
            }
            
        result.append({
            "booking_id": booking.id,
            "station_id": booking.station_id,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "total_cost": booking.total_cost,
            "status": booking.status,
            "expiration_time": booking.expiration_time,
            "payment": payment_info
        })
    
    return result


@router.get("/booking-details/{booking_id}", response_model=BookingWithPaymentResponse)
def get_booking_details(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)
):
    """
    Get detailed information about a booking including payment status
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Allow access only if the user owns the booking or is an admin
    if isinstance(current_user, User) and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    
    # Get the most recent payment for this booking
    payment = None
    if booking.payments:
        payment = max(booking.payments, key=lambda p: p.created_at)
        
    payment_info = None
    if payment:
        payment_info = {
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "status": payment.status,
            "approval_link": None  # Can't retrieve this after creation
        }
        
    return {
        "booking_id": booking.id,
        "station_id": booking.station_id,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "total_cost": booking.total_cost,
        "status": booking.status,
        "expiration_time": booking.expiration_time,
        "payment": payment_info
    }


@router.post("/cancel-booking/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)
):
    """
    Cancel a booking if it hasn't been paid for
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Allow cancellation only if the user owns the booking or is an admin
    if isinstance(current_user, User) and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    
    booking_service = BookingService(db)
    
    try:
        cancelled_booking = booking_service.cancel_booking(booking_id)
        return {"status": "success", "booking_id": cancelled_booking.id, "message": "Booking cancelled successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@router.post("/admin/process-expired-bookings")
def process_expired_bookings(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Manually trigger processing of expired bookings (admin only)
    """
    booking_service = BookingService(db)
    cancelled_count = booking_service.process_expired_bookings()
    
    return {"status": "success", "cancelled_bookings": cancelled_count}