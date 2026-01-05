"""User model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """User account with credits and subscription info."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    whop_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Credits
    credits: Mapped[int] = mapped_column(Integer, default=0)
    credits_used_total: Mapped[int] = mapped_column(Integer, default=0)

    # Subscription
    subscription_tier: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # starter, pro, scale

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    brand_profile: Mapped[Optional["BrandProfile"]] = relationship(
        "BrandProfile", back_populates="user", uselist=False
    )
    generations: Mapped[list["Generation"]] = relationship(
        "Generation", back_populates="user"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user"
    )

    def has_credits(self, amount: int = 1) -> bool:
        """Check if user has enough credits."""
        return self.credits >= amount

    def use_credits(self, amount: int) -> bool:
        """Use credits if available. Returns True if successful."""
        if self.has_credits(amount):
            self.credits -= amount
            self.credits_used_total += amount
            return True
        return False

    def add_credits(self, amount: int) -> None:
        """Add credits to user account."""
        self.credits += amount
