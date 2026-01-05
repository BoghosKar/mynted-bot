"""Brand profile model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Boolean, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BrandProfile(Base):
    """User's brand profile for consistent generation."""

    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # Brand info
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Style settings
    colors: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Hex codes or descriptions
    style_keywords: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Comma-separated
    avoid_list: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Things to avoid

    # Reference image analysis (stored as JSON from Claude Vision)
    reference_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reference_image_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )

    # Settings
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="brand_profile")

    def to_context_dict(self) -> dict:
        """Convert brand profile to context dictionary for AI pipeline."""
        if not self.enabled:
            return {}

        return {
            "brand_name": self.name,
            "industry": self.industry,
            "colors": self.colors,
            "style_keywords": self.style_keywords.split(",") if self.style_keywords else [],
            "avoid": self.avoid_list.split(",") if self.avoid_list else [],
            "reference_analysis": self.reference_analysis,
        }
