"""Whop webhook handler for payment processing."""

import hmac
import hashlib
import json
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.models.transaction import Transaction
from src.models import get_db

logger = logging.getLogger("whop_handler")

# Credit package mapping
CREDIT_PACKAGES = {}


def init_credit_packages():
    """Initialize credit package mapping from settings."""
    global CREDIT_PACKAGES

    if settings.whop_starter_product_id:
        CREDIT_PACKAGES[settings.whop_starter_product_id] = settings.whop_starter_credits
    if settings.whop_creator_product_id:
        CREDIT_PACKAGES[settings.whop_creator_product_id] = settings.whop_creator_credits
    if settings.whop_professional_product_id:
        CREDIT_PACKAGES[settings.whop_professional_product_id] = settings.whop_professional_credits
    if settings.whop_enterprise_product_id:
        CREDIT_PACKAGES[settings.whop_enterprise_product_id] = settings.whop_enterprise_credits

    logger.info(f"Initialized {len(CREDIT_PACKAGES)} Whop credit packages")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Whop webhook signature using HMAC SHA256.

    Args:
        payload: Raw request body bytes
        signature: Signature from Whop-Signature header
        secret: Webhook secret from Whop dashboard

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret:
        logger.warning("Whop webhook secret not configured")
        return False

    try:
        # Whop uses Standard Webhooks spec
        # Format: "v1,<timestamp>,<signature>"
        parts = signature.split(",")
        if len(parts) != 3 or parts[0] != "v1":
            logger.error(f"Invalid signature format: {signature}")
            return False

        timestamp = parts[1]
        expected_signature = parts[2]

        # Create signed content: timestamp.payload
        signed_content = f"{timestamp}.{payload.decode('utf-8')}"

        # Calculate HMAC
        calculated_signature = hmac.new(
            secret.encode('utf-8'),
            signed_content.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(calculated_signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


async def handle_payment_succeeded(payload: dict, db: AsyncSession) -> dict:
    """Handle successful payment webhook.

    Args:
        payload: Webhook payload with payment data
        db: Database session

    Returns:
        Response dict
    """
    try:
        # Extract payment data
        data = payload.get("data", {})
        payment_id = data.get("id")
        product_id = data.get("product_id")
        user_data = data.get("user", {})
        discord_id = user_data.get("social_accounts", {}).get("discord")
        amount = data.get("final_amount", 0) / 100  # Convert cents to dollars

        logger.info(f"Processing payment {payment_id} for product {product_id}")

        # Check if we have this product mapped to credits
        if product_id not in CREDIT_PACKAGES:
            logger.warning(f"Unknown product ID: {product_id}")
            return {"status": "ignored", "reason": "Unknown product"}

        credits_to_add = CREDIT_PACKAGES[product_id]

        # If no Discord ID linked, we can't add credits
        if not discord_id:
            logger.warning(f"Payment {payment_id} has no Discord account linked")
            return {"status": "error", "reason": "No Discord account linked"}

        # Get or create user
        from src.services.user_service import UserService
        user_service = UserService(db)
        user = await user_service.get_or_create_user(int(discord_id))

        # Add credits
        old_balance = user.credits
        user.credits += credits_to_add

        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            credits=credits_to_add,
            type="purchase",
            status="completed",
            payment_provider="whop",
            payment_id=payment_id,
            metadata={"product_id": product_id}
        )
        db.add(transaction)

        await db.commit()

        logger.info(
            f"Added {credits_to_add} credits to user {discord_id} "
            f"(balance: {old_balance} -> {user.credits})"
        )

        return {
            "status": "success",
            "user_id": discord_id,
            "credits_added": credits_to_add,
            "new_balance": user.credits
        }

    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}", exc_info=True)
        await db.rollback()
        return {"status": "error", "reason": str(e)}


async def handle_refund_created(payload: dict, db: AsyncSession) -> dict:
    """Handle refund created webhook.

    Args:
        payload: Webhook payload with refund data
        db: Database session

    Returns:
        Response dict
    """
    try:
        data = payload.get("data", {})
        payment_id = data.get("payment_id")
        refund_id = data.get("id")
        amount = data.get("amount", 0) / 100

        logger.info(f"Processing refund {refund_id} for payment {payment_id}")

        # Find the original transaction
        from sqlalchemy import select
        result = await db.execute(
            select(Transaction).where(Transaction.payment_id == payment_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(f"Transaction not found for payment {payment_id}")
            return {"status": "error", "reason": "Transaction not found"}

        # Deduct credits from user
        from src.services.user_service import UserService
        user_service = UserService(db)
        user = await user_service.get_user(transaction.user_id)

        if not user:
            logger.error(f"User not found for transaction {transaction.id}")
            return {"status": "error", "reason": "User not found"}

        old_balance = user.credits
        credits_to_remove = transaction.credits
        user.credits = max(0, user.credits - credits_to_remove)

        # Create refund transaction record
        refund_transaction = Transaction(
            user_id=user.id,
            amount=-amount,
            credits=-credits_to_remove,
            type="refund",
            status="completed",
            payment_provider="whop",
            payment_id=refund_id,
            metadata={"original_payment_id": payment_id}
        )
        db.add(refund_transaction)

        await db.commit()

        logger.info(
            f"Removed {credits_to_remove} credits from user (Discord ID: {user.discord_id}) "
            f"(balance: {old_balance} -> {user.credits})"
        )

        return {
            "status": "success",
            "credits_removed": credits_to_remove,
            "new_balance": user.credits
        }

    except Exception as e:
        logger.error(f"Error processing refund webhook: {e}", exc_info=True)
        await db.rollback()
        return {"status": "error", "reason": str(e)}


# FastAPI app for webhook endpoint
app = FastAPI(title="Mynted Whop Webhooks")


@app.on_event("startup")
async def startup():
    """Initialize webhook handler on startup."""
    init_credit_packages()


@app.post("/webhooks/whop")
async def whop_webhook(
    request: Request,
    whop_signature: Optional[str] = Header(None, alias="Whop-Signature")
):
    """Handle Whop webhook events.

    Args:
        request: FastAPI request object
        whop_signature: Webhook signature header

    Returns:
        JSON response
    """
    try:
        # Read raw body
        body = await request.body()

        # Verify signature
        if not settings.whop_webhook_secret:
            logger.warning("Whop webhook secret not configured - skipping verification")
        elif not whop_signature:
            logger.error("Missing Whop-Signature header")
            raise HTTPException(status_code=401, detail="Missing signature")
        elif not verify_webhook_signature(body, whop_signature, settings.whop_webhook_secret):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        event_type = payload.get("type")
        logger.info(f"Received Whop webhook: {event_type}")

        # Get database session
        async for db in get_db():
            # Handle different event types
            if event_type == "payment.succeeded":
                result = await handle_payment_succeeded(payload, db)
            elif event_type == "refund.created":
                result = await handle_refund_created(payload, db)
            else:
                logger.info(f"Ignoring webhook event: {event_type}")
                result = {"status": "ignored", "event_type": event_type}

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whop-webhooks"}
