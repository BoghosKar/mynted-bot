"""Generation service for database operations."""

from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Generation


class GenerationService:
    """Service for generation-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_generation(
        self,
        discord_id: int,
        form_inputs: dict,
        image_count: int,
        variation_style: str = "diverse",
        content_type: Optional[str] = None,
        platform: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        brand_profile_used: bool = False,
        reference_hash: Optional[str] = None,
        thread_id: Optional[int] = None,
    ) -> Generation:
        """Create a new generation record."""
        # Get user
        result = await self.session.execute(
            select(User).where(User.discord_id == discord_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {discord_id}")

        generation = Generation(
            user_id=user.id,
            form_inputs=form_inputs,
            image_count=image_count,
            credits_used=image_count,  # 1 credit per image
            variation_style=variation_style,
            content_type=content_type,
            platform=platform,
            aspect_ratio=aspect_ratio,
            brand_profile_used=brand_profile_used,
            reference_hash=reference_hash,
            thread_id=thread_id,
        )

        self.session.add(generation)
        await self.session.commit()
        await self.session.refresh(generation)

        return generation

    async def update_generation_context(
        self,
        generation_id: int,
        context_profile: dict,
        prompts_used: list[str],
    ) -> None:
        """Update generation with AI pipeline output."""
        result = await self.session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()

        if generation:
            generation.context_profile = context_profile
            generation.prompts_used = prompts_used
            await self.session.commit()

    async def mark_generation_completed(
        self,
        generation_id: int,
        success_count: int,
        fail_count: int,
        message_id: Optional[int] = None,
    ) -> None:
        """Mark generation as completed."""
        result = await self.session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()

        if generation:
            generation.mark_completed(success_count, fail_count)
            if message_id:
                generation.message_id = message_id
            await self.session.commit()

    async def set_generation_rating(
        self, generation_id: int, rating: str
    ) -> None:
        """Set rating for a generation."""
        result = await self.session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()

        if generation:
            generation.set_rating(rating)
            await self.session.commit()

    async def mark_regenerated(self, generation_id: int) -> None:
        """Mark a generation as regenerated."""
        result = await self.session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        generation = result.scalar_one_or_none()

        if generation:
            generation.regenerated = True
            await self.session.commit()

    async def get_user_history(
        self, discord_id: int, limit: int = 10
    ) -> list[Generation]:
        """Get user's recent generations."""
        result = await self.session.execute(
            select(User).where(User.discord_id == discord_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return []

        result = await self.session.execute(
            select(Generation)
            .where(Generation.user_id == user.id)
            .order_by(desc(Generation.created_at))
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_generation(self, generation_id: int) -> Optional[Generation]:
        """Get a generation by ID."""
        result = await self.session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        return result.scalar_one_or_none()

    async def get_generations_for_learning(
        self,
        industry: Optional[str] = None,
        content_type: Optional[str] = None,
        min_rating: str = "good",
    ) -> list[Generation]:
        """Get generations for learning engine analysis."""
        # Rating hierarchy: amazing > good > okay > bad
        rating_map = {"amazing": 4, "good": 3, "okay": 2, "bad": 1}
        min_rating_value = rating_map.get(min_rating, 3)

        query = select(Generation).where(Generation.rating.isnot(None))

        if industry:
            # Filter by industry through context_profile
            query = query.where(
                Generation.context_profile["industry"].astext == industry
            )

        if content_type:
            query = query.where(Generation.content_type == content_type)

        result = await self.session.execute(query)
        generations = list(result.scalars().all())

        # Filter by rating in Python (simpler than complex SQL)
        return [
            g
            for g in generations
            if rating_map.get(g.rating, 0) >= min_rating_value
        ]
