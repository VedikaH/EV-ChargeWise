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
from app.services.payment_tasks import check_payment_status

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