"""User service for database operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, BrandProfile, Transaction


class UserService:
    """Service for user-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, discord_id: int) -> User:
        """Get user by Discord ID, or create if doesn't exist."""
        result = await self.session.execute(
            select(User).where(User.discord_id == discord_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(discord_id=discord_id, credits=0)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        return user

    async def get_user(self, discord_id: int) -> Optional[User]:
        """Get user by Discord ID."""
        result = await self.session.execute(
            select(User).where(User.discord_id == discord_id)
        )
        return result.scalar_one_or_none()

    async def get_user_credits(self, discord_id: int) -> int:
        """Get user's current credit balance."""
        user = await self.get_user(discord_id)
        return user.credits if user else 0

    async def use_credits(self, discord_id: int, amount: int, generation_id: int) -> bool:
        """Use credits for a generation. Returns True if successful."""
        user = await self.get_or_create_user(discord_id)

        if not user.has_credits(amount):
            return False

        user.use_credits(amount)

        # Create transaction record
        transaction = Transaction.create_usage(user.id, amount, generation_id)
        self.session.add(transaction)

        await self.session.commit()
        return True

    async def add_credits(
        self, discord_id: int, amount: int, transaction_type: str, description: str
    ) -> None:
        """Add credits to user account."""
        user = await self.get_or_create_user(discord_id)
        user.add_credits(amount)

        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            type=transaction_type,
            amount=amount,
            description=description,
        )
        self.session.add(transaction)

        await self.session.commit()

    async def refund_credits(
        self, discord_id: int, amount: int, reason: str
    ) -> None:
        """Refund credits for a failed generation."""
        user = await self.get_or_create_user(discord_id)
        user.add_credits(amount)

        transaction = Transaction.create_refund(user.id, amount, reason)
        self.session.add(transaction)

        await self.session.commit()

    async def get_brand_profile(self, discord_id: int) -> Optional[BrandProfile]:
        """Get user's brand profile."""
        user = await self.get_user(discord_id)
        if not user:
            return None

        result = await self.session.execute(
            select(BrandProfile).where(BrandProfile.user_id == user.id)
        )
        return result.scalar_one_or_none()

    async def save_brand_profile(
        self,
        discord_id: int,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        colors: Optional[str] = None,
        style_keywords: Optional[str] = None,
        avoid_list: Optional[str] = None,
    ) -> BrandProfile:
        """Create or update user's brand profile."""
        user = await self.get_or_create_user(discord_id)

        result = await self.session.execute(
            select(BrandProfile).where(BrandProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = BrandProfile(user_id=user.id)
            self.session.add(profile)

        if name is not None:
            profile.name = name
        if industry is not None:
            profile.industry = industry
        if colors is not None:
            profile.colors = colors
        if style_keywords is not None:
            profile.style_keywords = style_keywords
        if avoid_list is not None:
            profile.avoid_list = avoid_list

        await self.session.commit()
        await self.session.refresh(profile)

        return profile

    async def toggle_brand_profile(self, discord_id: int) -> bool:
        """Toggle brand profile enabled state. Returns new state."""
        profile = await self.get_brand_profile(discord_id)
        if not profile:
            return False

        profile.enabled = not profile.enabled
        await self.session.commit()

        return profile.enabled

    async def update_subscription(
        self, discord_id: int, tier: str, whop_user_id: str
    ) -> None:
        """Update user's subscription tier."""
        user = await self.get_or_create_user(discord_id)
        user.subscription_tier = tier
        user.whop_user_id = whop_user_id
        await self.session.commit()
