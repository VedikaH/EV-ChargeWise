from typing import Any, Dict, Union
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.base import Base
from app.schemas.bookings import PaymentRequest, PaymentResponse
from app.services.payment_services import PayPalService
from app.models.payments import Payment
from app.auth.dependencies import get_current_user
from app.models.admin import Admin
from app.models.bookings import Booking
from app.models.user import User

router = APIRouter()

# @router.post("/create-order", response_model=PaymentResponse)
# def create_payment_order(
#     payment_request: PaymentRequest,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         order = paypal_service.create_order(
#             amount=payment_request.amount / 100,  # Convert from paisa/cents
#             currency=payment_request.currency,
#             invoice_id=str(payment_request.booking_id) if payment_request.booking_id else None
#         )
        
#         # Store payment information
#         payment = Payment(
#             order_id=order['id'],
#             booking_id=payment_request.booking_id,
#             amount=payment_request.amount / 100,
#             currency=payment_request.currency,
#             status=order.get('status', 'created')
#         )
#         db.add(payment)
#         db.commit()
#         db.refresh(payment)
        
#         return {
#             "order_id": order['id'], 
#             "approval_link": next(
#                 (link['href'] for link in order.get('links', []) 
#                  if link['rel'] == 'payer-action'),
#                 None
#             )
#         }
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-order", response_model=PaymentResponse)
def create_payment_order(
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Enforce authentication
):
    paypal_service = PayPalService()

    # Validate booking ownership
    if payment_request.booking_id:
        booking = db.query(Booking).filter(Booking.id == payment_request.booking_id).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Ensure that only the user who made the booking can make a payment (unless admin)
        if isinstance(current_user, User) and booking.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to pay for this booking")

    try:
        order = paypal_service.create_order(
            amount=payment_request.amount / 100,  # Convert from paisa/cents
            currency=payment_request.currency,
            invoice_id=str(payment_request.booking_id) if payment_request.booking_id else None
        )

        # Store payment information
        payment = Payment(
            user_id=current_user.id,  # Track who made the payment
            order_id=order['id'],
            booking_id=payment_request.booking_id,
            amount=payment_request.amount / 100,
            currency=payment_request.currency,
            status=order.get('status', 'created')
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "order_id": order['id'], 
            "approval_link": next(
                (link['href'] for link in order.get('links', []) 
                 if link['rel'] == 'payer-action'),
                None
            )
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/verify-order/{order_id}")
# def verify_order(
#     order_id: str,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         order_details = paypal_service.verify_order(order_id)
        
#         # Update payment status in database
#         payment = db.query(Payment).filter(Payment.order_id == order_id).first()
#         if payment:
#             payment.status = order_details['status']
#             db.commit()
        
#         return {
#             "status": order_details['status'],
#             "details": order_details
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
@router.get("/verify-order/{order_id}")
def verify_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Enforce authentication
):
    paypal_service = PayPalService()

    # Fetch payment from the database
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure only the user who made the payment or an admin can verify it
    if isinstance(current_user, User) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to verify this payment")

    try:
        order_details = paypal_service.verify_order(order_id)

        # Update payment status in the database
        payment.status = order_details.get("status", payment.status)
        db.commit()
        db.refresh(payment)

        return {
            "status": payment.status,
            "details": order_details
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# @router.post("/confirm-order/{order_id}")
# def confirm_order(
#     order_id: str, 
#     payment_source: Dict[str, Any],
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         confirmation_result = paypal_service.confirm_order(
#             order_id=order_id, 
#             payment_source=payment_source
#         )
        
#         # Update payment status
#         payment = db.query(Payment).filter(Payment.order_id == order_id).first()
#         if payment:
#             payment.status = 'confirmed'
#             db.commit()
        
#         return {
#             "status": "confirmed",
#             "details": confirmation_result
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.post("/confirm-order/{order_id}")
def confirm_order(
    order_id: str, 
    payment_source: Dict[str, Any] = Body(...),  # Ensure `payment_source` is in the request body
    db: Session = Depends(get_db),
    current_user: Union[User, Admin] = Depends(get_current_user)  # Require authentication
):
    paypal_service = PayPalService()

    # Fetch payment from the database
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure only the owner of the payment or an admin can confirm it
    if isinstance(current_user, User) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to confirm this payment")

    try:
        confirmation_result = paypal_service.confirm_order(
            order_id=order_id, 
            payment_source=payment_source
        )

        # Extract payment status from PayPal response
        payment_status = confirmation_result.get("status", "failed")

        # Update payment status in the database
        payment.status = payment_status
        db.commit()
        db.refresh(payment)

        return {
            "status": payment_status,
            "details": confirmation_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @router.post("/capture-order/{order_id}")
# def capture_order(
#     order_id: str,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         capture_result = paypal_service.capture_order(order_id)
        
#         # Update payment status
#         payment = db.query(Payment).filter(Payment.order_id == order_id).first()
#         if payment:
#             payment.status = capture_result['status']
            
#             # Optional: Update associated booking status
#             if payment.booking:
#                 payment.booking.status = 'paid'
            
#             db.commit()
        
#         return {
#             "status": "success",
#             "details": capture_result
#         }
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=400, detail=str(e))


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

        return {
            "status": payment_status,
            "details": capture_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# from typing import Any, Dict
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session

# from app.database.session import get_db
# from app.schemas.bookings import PaymentRequest, PaymentResponse
# from app.services.payment_services import PayPalService

# router = APIRouter()

# @router.post("/create-order", response_model=PaymentResponse)
# def create_payment_order(
#     payment_request: PaymentRequest,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         order = paypal_service.create_order(
#             amount=payment_request.amount,
#             currency=payment_request.currency
#         )
#         return {
#             "order_id": order['id'], 
#             "approval_link": next(
#                 (link['href'] for link in order.get('links', []) 
#                  if link['rel'] == 'payer-action'),
#                 None
#             )
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/verify-order/{order_id}")
# def verify_order(
#     order_id: str,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         order_details = paypal_service.verify_order(order_id)
#         return {
#             "status": order_details['status'],
#             "details": order_details
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
# @router.post("/confirm-order/{order_id}")
# def confirm_order(
#     order_id: str, 
#     payment_source: Dict[str, Any],
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         confirmation_result = paypal_service.confirm_order(
#             order_id=order_id, 
#             payment_source=payment_source
#         )
#         return {
#             "status": "confirmed",
#             "details": confirmation_result
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/capture-order/{order_id}")
# def capture_order(
#     order_id: str,
#     db: Session = Depends(get_db)
# ):
#     paypal_service = PayPalService()
    
#     try:
#         capture_result = paypal_service.capture_order(order_id)
#         return {
#             "status": "success",
#             "details": capture_result
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))