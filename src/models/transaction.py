"""Transaction model for payment tracking."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Transaction(Base):
    """Record of credit transactions."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Transaction type: purchase, refund, grant, use
    type: Mapped[str] = mapped_column(String(20))

    # Amount (positive for add, negative for use)
    amount: Mapped[int] = mapped_column(Integer)

    # Payment reference
    whop_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Description
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")

    @classmethod
    def create_purchase(
        cls, user_id: int, amount: int, whop_payment_id: str, tier: str
    ) -> "Transaction":
        """Create a purchase transaction."""
        return cls(
            user_id=user_id,
            type="purchase",
            amount=amount,
            whop_payment_id=whop_payment_id,
            description=f"Subscription: {tier}",
        )

    @classmethod
    def create_usage(
        cls, user_id: int, amount: int, generation_id: int
    ) -> "Transaction":
        """Create a usage transaction."""
        return cls(
            user_id=user_id,
            type="use",
            amount=-amount,
            description=f"Generation #{generation_id}",
        )

    @classmethod
    def create_refund(
        cls, user_id: int, amount: int, reason: str
    ) -> "Transaction":
        """Create a refund transaction."""
        return cls(
            user_id=user_id,
            type="refund",
            amount=amount,
            description=f"Refund: {reason}",
        )

    @classmethod
    def create_grant(
        cls, user_id: int, amount: int, reason: str
    ) -> "Transaction":
        """Create a grant transaction (admin adds credits)."""
        return cls(
            user_id=user_id,
            type="grant",
            amount=amount,
            description=f"Grant: {reason}",
        )
