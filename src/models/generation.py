"""Generation model for tracking image generations."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Integer, Text, Boolean, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Generation(Base):
    """Record of an image generation request."""

    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Form inputs (raw from Discord modal)
    form_inputs: Mapped[dict] = mapped_column(JSON)

    # AI pipeline data
    context_profile: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Output from Context Builder
    prompts_used: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # Final TEXT prompts sent to Gemini

    # Generation settings
    content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    variation_style: Mapped[str] = mapped_column(
        String(20), default="diverse"
    )  # diverse, subtle, consistent
    image_count: Mapped[int] = mapped_column(Integer)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Results
    credits_used: Mapped[int] = mapped_column(Integer)
    images_generated: Mapped[int] = mapped_column(Integer, default=0)
    images_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Feedback (learning engine data)
    rating: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # amazing, good, okay, bad
    regenerated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Reference
    reference_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    brand_profile_used: Mapped[bool] = mapped_column(Boolean, default=False)

    # Discord context
    thread_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generations")

    def mark_completed(self, success_count: int, fail_count: int) -> None:
        """Mark generation as completed."""
        self.images_generated = success_count
        self.images_failed = fail_count
        self.completed_at = datetime.utcnow()

    def set_rating(self, rating: str) -> None:
        """Set user rating for this generation."""
        valid_ratings = ["amazing", "good", "okay", "bad"]
        if rating.lower() in valid_ratings:
            self.rating = rating.lower()
