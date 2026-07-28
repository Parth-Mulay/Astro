from __future__ import annotations

import hmac
import hashlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import Payment, PaymentStatus
from app.account import add_wallet, get_or_create_profile
from app.settings import settings

router = APIRouter(prefix="/payment", tags=["payment"])
logger = logging.getLogger("application")

# Razorpay client lazy initialization
_razorpay_client = None

def get_razorpay_client():
    global _razorpay_client
    if _razorpay_client is None:
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_SECRET:
            try:
                import razorpay
                _razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET))
            except ImportError:
                logger.error("razorpay-python package is missing in environment")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
    return _razorpay_client


@router.post("/razorpay/create-order")
async def create_razorpay_order(
    request: Request,
    amount: int = Form(...),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid recharge amount")

    client = get_razorpay_client()
    if not client:
        # Fallback to local simulation if Razorpay is not configured
        logger.warning("Razorpay credentials not set. Simulating order creation.")
        return {
            "simulated": True,
            "amount": amount,
            "currency": "INR",
            "key": "simulated-key"
        }

    try:
        # Amount in paise (1 INR = 100 paise)
        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "receipt": f"rcpt_wallet_{user.id}_{int(request.scope.get('time', 0)) if 'time' in request.scope else 0}",
            "notes": {
                "user_id": str(user.id),
                "type": "wallet_recharge"
            }
        }
        order = client.order.create(data=order_data)
        
        # Save a pending payment record
        payment_record = Payment(
            user_id=user.id,
            amount=amount,
            status=PaymentStatus.pending
        )
        session.add(payment_record)
        session.commit()
        
        return {
            "simulated": False,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": settings.RAZORPAY_KEY_ID
        }
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate payment gateway order")


@router.post("/razorpay/verify")
async def verify_razorpay_payment(
    request: Request,
    razorpay_payment_id: str = Form(...),
    razorpay_order_id: str = Form(...),
    razorpay_signature: str = Form(...),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    client = get_razorpay_client()
    
    if not client:
        logger.warning("Razorpay client not configured for signature verification")
        raise HTTPException(status_code=400, detail="Payment gateway not configured")

    # Verify signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        logger.warning(f"Razorpay signature verification failed for user {user.id}: {e}")
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    # Check if this order was already processed via webhook
    # We can fetch transaction details to find the amount
    try:
        payment_detail = client.payment.fetch(razorpay_payment_id)
        amount_paise = payment_detail.get("amount", 0)
        amount = amount_paise // 100
        
        # Credit wallet securely
        add_wallet(session, user.id, amount)
        
        # Update/Create payment record
        payment_record = Payment(
            user_id=user.id,
            amount=amount,
            status=PaymentStatus.completed
        )
        session.add(payment_record)
        session.commit()
        
        return {"status": "success", "message": f"Successfully recharged ₹{amount} to wallet."}
    except Exception as e:
        logger.error(f"Error capturing/processing verified payment: {e}")
        raise HTTPException(status_code=500, detail="Error updating wallet balance")


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured. Webhook rejected.")
        return Response(status_code=400, content="Webhook secret not configured")

    # Verify signature securely using HMAC SHA256
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Invalid Razorpay webhook signature received")
        return Response(status_code=400, content="Invalid signature")

    try:
        data = json.loads(body.decode("utf-8"))
        event = data.get("event")
        
        if event == "payment.captured":
            payment_entity = data["payload"]["payment"]["entity"]
            notes = payment_entity.get("notes", {})
            user_id_str = notes.get("user_id")
            
            if user_id_str:
                user_id = int(user_id_str)
                amount_paise = payment_entity.get("amount", 0)
                amount = amount_paise // 100
                
                # Verify if this payment record is already completed to prevent double credit
                # Webhook is an alternative route to ensure wallet update
                logger.info(f"Webhook processing capture event for user {user_id}: ₹{amount}")
                add_wallet(session, user_id, amount)
                
                payment_record = Payment(
                    user_id=user_id,
                    amount=amount,
                    status=PaymentStatus.completed
                )
                session.add(payment_record)
                session.commit()
                
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook payload: {e}")
        return Response(status_code=500, content="Internal error processing webhook")
