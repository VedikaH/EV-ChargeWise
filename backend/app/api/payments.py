from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.base import Base
from app.schemas.bookings import PaymentRequest, PaymentResponse
from app.services.payment_services import PayPalService
from app.models.payments import Payment

router = APIRouter()

@router.post("/create-order", response_model=PaymentResponse)
def create_payment_order(
    payment_request: PaymentRequest,
    db: Session = Depends(get_db)
):
    paypal_service = PayPalService()
    
    try:
        order = paypal_service.create_order(
            amount=payment_request.amount / 100,  # Convert from paisa/cents
            currency=payment_request.currency,
            invoice_id=str(payment_request.booking_id) if payment_request.booking_id else None
        )
        
        # Store payment information
        payment = Payment(
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

@router.get("/verify-order/{order_id}")
def verify_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    paypal_service = PayPalService()
    
    try:
        order_details = paypal_service.verify_order(order_id)
        
        # Update payment status in database
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = order_details['status']
            db.commit()
        
        return {
            "status": order_details['status'],
            "details": order_details
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/confirm-order/{order_id}")
def confirm_order(
    order_id: str, 
    payment_source: Dict[str, Any],
    db: Session = Depends(get_db)
):
    paypal_service = PayPalService()
    
    try:
        confirmation_result = paypal_service.confirm_order(
            order_id=order_id, 
            payment_source=payment_source
        )
        
        # Update payment status
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = 'confirmed'
            db.commit()
        
        return {
            "status": "confirmed",
            "details": confirmation_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/capture-order/{order_id}")
def capture_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    paypal_service = PayPalService()
    
    try:
        capture_result = paypal_service.capture_order(order_id)
        
        # Update payment status
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = capture_result['status']
            
            # Optional: Update associated booking status
            if payment.booking:
                payment.booking.status = 'paid'
            
            db.commit()
        
        return {
            "status": "success",
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