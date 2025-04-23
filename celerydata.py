#celery_app.py
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "app",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.payment_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max task runtime
)

# Optional: Configure scheduled tasks
celery_app.conf.beat_schedule = {
    'check-pending-payments-every-5-minutes': {
        'task': 'app.tasks.payment_tasks.check_pending_payments',
        'schedule': 300.0,  # 5 minutes
    },
}

#config.py
from pydantic import BaseSettings
from typing import Optional, Dict, Any
import os
from pathlib import Path

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # PayPal settings
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_RETURN_URL: str = os.getenv("PAYPAL_RETURN_URL", "http://localhost:8000/payment-success")
    PAYPAL_CANCEL_URL: str = os.getenv("PAYPAL_CANCEL_URL", "http://localhost:8000/payment-cancelled")
    
    # Redis and Celery settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Payment timeout (minutes)
    PAYMENT_TIMEOUT_MINUTES: int = 15

    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

#models/booking.py
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_cost = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, confirmed, paid, cancelled, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    station = relationship("Station", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False)

#models/payment.py
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=True)
    order_id = Column(String(255), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="created")  # created, approved, captured, cancelled, refunded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payment_method = Column(String(50), default="paypal")
    transaction_id = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", back_populates="payment", uselist=False)

#payment_tasks.py
from app.celery_app import celery_app
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.bookings import Booking
from app.models.payments import Payment
from app.services.payment_services import PayPalService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def check_payment_status(payment_id: int, order_id: str):
    """
    Check the status of a payment and update the booking status accordingly
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        
        if not payment:
            logger.error(f"Payment with ID {payment_id} not found")
            return {"status": "error", "message": "Payment not found"}
        
        if payment.status in ["COMPLETED", "captured", "paid"]:
            logger.info(f"Payment {payment_id} already completed")
            return {"status": "success", "message": "Payment already completed"}
        
        # Check with PayPal
        paypal_service = PayPalService()
        try:
            order_details = paypal_service.verify_order(order_id)
            payment_status = order_details.get("status", "PENDING")
            
            # Update payment status
            payment.status = payment_status
            
            # Update booking status if payment completed
            if payment_status in ["COMPLETED", "APPROVED"]:
                if payment.booking:
                    payment.booking.status = "confirmed"
                    logger.info(f"Booking {payment.booking_id} confirmed after successful payment")
            
            db.commit()
            logger.info(f"Payment {payment_id} status updated to {payment_status}")
            
            return {
                "status": "success", 
                "payment_status": payment_status,
                "booking_id": payment.booking_id if payment.booking else None
            }
            
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task
def expire_pending_payment(payment_id: int, booking_id: int):
    """
    Cancel a booking and mark payment as expired if not completed within timeout
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not payment or not booking:
            logger.error(f"Payment {payment_id} or Booking {booking_id} not found")
            return {"status": "error", "message": "Payment or Booking not found"}
        
        # Only expire if still pending
        if payment.status in ["created", "pending", "CREATED", "PENDING"] and booking.status == "pending":
            payment.status = "expired"
            booking.status = "expired"
            db.commit()
            logger.info(f"Payment {payment_id} and Booking {booking_id} expired due to timeout")
            return {"status": "success", "message": "Payment and booking expired"}
        else:
            logger.info(f"Payment {payment_id} with status {payment.status} not eligible for expiration")
            return {"status": "skipped", "message": "Payment not in pending state"}
    
    finally:
        db.close()

@celery_app.task
def check_pending_payments():
    """
    Periodic task to check all pending payments and expire those that have timed out
    """
    db = SessionLocal()
    try:
        # Find payments that are pending and older than the timeout
        timeout_minutes = settings.PAYMENT_TIMEOUT_MINUTES
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        pending_payments = db.query(Payment).filter(
            Payment.status.in_(["created", "pending", "CREATED", "PENDING"]),
            Payment.created_at < cutoff_time
        ).all()
        
        results = []
        for payment in pending_payments:
            # Get associated booking
            if payment.booking and payment.booking.status == "pending":
                # Expire the payment and booking
                payment.status = "expired"
                payment.booking.status = "expired"
                results.append({
                    "payment_id": payment.id,
                    "booking_id": payment.booking_id,
                    "status": "expired"
                })
        
        if results:
            db.commit()
            logger.info(f"Expired {len(results)} pending payments and bookings")
        
        return results
    
    finally:
        db.close()

#app/services/booking_services.py
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
from app.tasks.payment_tasks import check_payment_status, expire_pending_payment
from app.core.config import settings


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
        
        # Create booking
        new_booking = Booking(
            user_id=user_id,
            station_id=booking_data.station_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            total_cost=booking_data.total_cost,
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

#app/api/v1/bookings.py   
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Union, Dict, Any

from app.database.session import get_db
from app.models.bookings import Booking
from app.models.stations import Station
from app.schemas.bookings import BookingCreate, BookingResponse, BookingWithPaymentResponse
from app.services.booking_services import BookingService
from app.models.admin import Admin
from app.auth.dependencies import get_current_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.post("/create-booking", response_model=BookingWithPaymentResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ensure only authenticated users can book
):
    # Create booking service
    booking_service = BookingService(db)
    
    try:
        result = booking_service.create_booking(booking, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-bookings", response_model=List[BookingResponse])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Ensure only the logged-in user can access their bookings
):
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    return bookings

@router.get("/booking/{booking_id}", response_model=BookingWithPaymentResponse)
def get_booking_with_payment(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Authenticated user or admin
):
    booking_service = BookingService(db)
    
    try:
        # Get booking details
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Allow access only if the user owns the booking or is an admin
        if isinstance(current_user, User) and booking.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this booking")
        
        # Get payment status
        payment_info = booking_service.get_booking_payment_status(booking_id)
        
        return {
            "booking": booking,
            "payment": payment_info.get("payment_details") 
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/booking/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Authenticated user or admin
):
    booking_service = BookingService(db)
    
    try:
        # Get user ID for regular users (not admins)
        user_id = current_user.id if isinstance(current_user, User) else None
        
        # Cancel booking
        updated_booking = booking_service.cancel_booking(booking_id, user_id)
        return updated_booking
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

#app/api/v1/payments.py
from typing import Any, Dict, Union
from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.bookings import PaymentRequest, PaymentResponse
from app.services.payment_services import PayPalService
from app.models.payments import Payment
from app.models.bookings import Booking
from app.auth.dependencies import get_current_user
from app.models.admin import Admin
from app.models.user import User
from app.tasks.payment_tasks import check_payment_status

router = APIRouter()

@router.get("/payment/{payment_id}", response_model=Dict[str, Any])
def get_payment_details(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Require authentication
):
    # Fetch payment from the database
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure only the user who made the payment or an admin can access it
    if isinstance(current_user, User) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to view this payment")

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "created_at": payment.created_at,
        "booking_id": payment.booking_id
    }

@router.post("/verify-payment/{payment_id}")
def verify_payment(
    payment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Enforce authentication
):
    # Fetch payment from the database
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure only the user who made the payment or an admin can verify it
    if isinstance(current_user, User) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to verify this payment")

    # Queue the payment verification task
    background_tasks.add_task(check_payment_status, payment.id, payment.order_id)

    return {
        "message": "Payment verification queued",
        "payment_id": payment_id,
        "order_id": payment.order_id
    }

@router.post("/capture-order/{order_id}")
def capture_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Require authentication
):
    paypal_service = PayPalService()

    # Fetch payment from the database
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure only the owner of the payment or an admin can capture it
    if isinstance(current_user, User) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to capture this payment")

    try:
        capture_result = paypal_service.capture_order(order_id)

        # Extract payment status from PayPal response
        payment_status = capture_result.get("status", "failed")
        payment.status = payment_status

        # Update associated booking status if payment is successful
        if payment_status == "COMPLETED" and payment.booking:
            payment.booking.status = "paid"

        db.commit()
        db.refresh(payment)
        
        # If booking exists, refresh it too
        if payment.booking:
            db.refresh(payment.booking)

        return {
            "status": payment_status,
            "details": capture_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Webhook handler for PayPal payment status updates
@router.post("/webhook/paypal")
async def handle_paypal_webhook(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Handle PayPal webhooks for payment status updates"""
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    order_id = resource.get("id")
    
    if not order_id:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    
    # Find associated payment
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Update payment status based on event type
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        payment.status = "COMPLETED"
        
        # Update booking status
        if payment.booking:
            payment.booking.status = "paid"
            
        db.commit()
    elif event_type == "PAYMENT.CAPTURE.DENIED":
        payment.status = "DENIED"
        db.commit()
    
    return {"status": "success"}

#boolings_schemas.py
from pydantic import BaseModel, validator, Field
from datetime import datetime
from typing import Optional, Dict, Any

class BookingBase(BaseModel):
    station_id: int
    start_time: datetime
    end_time: datetime
    total_cost: float

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class BookingCreate(BookingBase):
    pass

class BookingResponse(BookingBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class PaymentRequest(BaseModel):
    booking_id: Optional[int] = None
    amount: float = Field(..., gt=0)  # Must be greater than 0
    currency: str = "USD"

class PaymentResponse(BaseModel):
    order_id: str
    approval_link: Optional[str] = None

class PaymentDetails(BaseModel):
    payment_id: int
    order_id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class BookingWithPaymentResponse(BaseModel):
    booking: BookingResponse
    payment: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

#docker_compose
version: '3.8'

services:
  # PostgreSQL database
  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=charging_stations
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis for Celery broker and result backend
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # FastAPI application
  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/charging_stations
      - REDIS_URL=redis://redis:6379/0
      - PAYPAL_BASE_URL=${PAYPAL_BASE_URL}
      - PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID}
      - PAYPAL_CLIENT_SECRET=${PAYPAL_CLIENT_SECRET}
      - PAYPAL_RETURN_URL=${PAYPAL_RETURN_URL:-http://localhost:8000/payment-success}
      - PAYPAL_CANCEL_URL=${PAYPAL_CANCEL_URL:-http://localhost:8000/payment-cancelled}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-super-secret-key}
    depends_on:
      - db
      - redis

  # Celery worker
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.celery_app worker --loglevel=info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/charging_stations
      - REDIS_URL=redis://redis:6379/0
      - PAYPAL_BASE_URL=${PAYPAL_BASE_URL}
      - PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID}
      - PAYPAL_CLIENT_SECRET=${PAYPAL_CLIENT_SECRET}
    depends_on:
      - db
      - redis
      - api

  # Celery beat scheduler for periodic tasks
  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.celery_app beat --loglevel=info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/charging_stations
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
      - api
      - celery_worker

  # Flower - Celery monitoring tool
  flower:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - celery_worker

volumes:
  postgres_data:

#docker_file fro project
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Command will be overridden by docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]