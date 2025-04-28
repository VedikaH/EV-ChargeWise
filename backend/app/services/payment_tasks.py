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