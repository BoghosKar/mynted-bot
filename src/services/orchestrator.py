"""Orchestrator - Ties the entire AI pipeline together.

Coordinates the flow:
1. Context Builder (form inputs -> JSON context)
2. Prompt Architect (JSON context -> TEXT prompts)
3. Image Generator (TEXT prompts -> images)
4. Delivery (images -> Discord)
"""

import discord
from typing import Optional, Callable, Any

from src.models import async_session
from src.services.user_service import UserService
from src.services.generation_service import GenerationService
from src.services.context_builder import ContextBuilder
from src.services.prompt_architect import PromptArchitect
from src.services.image_generator import ImageGenerator
from src.services.delivery import DeliveryService


class Orchestrator:
    """
    Orchestrates the complete image generation pipeline.

    This is the main entry point for processing a generation request.
    """

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.prompt_architect = PromptArchitect()
        self.image_generator = ImageGenerator()
        self.delivery = DeliveryService()

    async def process_generation(
        self,
        channel: discord.TextChannel,
        user_id: int,
        form_inputs: dict,
        reference_image: Optional[bytes] = None,
        status_message: Optional[discord.Message] = None,
    ) -> bool:
        """
        Process a complete generation request.

        Args:
            channel: Discord channel for output
            user_id: Discord user ID
            form_inputs: Form data from Discord modal
            reference_image: Optional reference image bytes
            status_message: Optional message to update with progress

        Returns:
            True if successful, False otherwise
        """
        async with async_session() as session:
            user_service = UserService(session)
            generation_service = GenerationService(session)

            # Get user and check credits
            user = await user_service.get_or_create_user(user_id)
            image_count = form_inputs.get("image_count", 5)

            if not user.has_credits(image_count):
                if status_message:
                    await status_message.edit(
                        content=f"Insufficient credits. You need {image_count} but have {user.credits}."
                    )
                return False

            # Get brand profile if enabled
            brand_profile = None
            if form_inputs.get("use_brand_profile"):
                profile = await user_service.get_brand_profile(user_id)
                if profile and profile.enabled:
                    brand_profile = profile.to_context_dict()

            # Create generation record
            generation = await generation_service.create_generation(
                discord_id=user_id,
                form_inputs=form_inputs,
                image_count=image_count,
                variation_style=form_inputs.get("variation_style", "diverse"),
                content_type=form_inputs.get("content_type"),
                platform=form_inputs.get("platform"),
                brand_profile_used=brand_profile is not None,
                reference_hash=form_inputs.get("reference_hash"),
            )

            # Use credits
            await user_service.use_credits(user_id, image_count, generation.id)

        # Update status
        if status_message:
            await status_message.edit(content="Building context profile...")

        # Step 1: Analyze reference image if provided
        reference_analysis = None
        if reference_image:
            try:
                reference_analysis = await self.context_builder.analyze_reference_image(
                    reference_image
                )
            except Exception as e:
                print(f"Reference analysis failed: {e}")

        # Step 2: Build context profile
        try:
            context_profile = await self.context_builder.build_context(
                form_inputs=form_inputs,
                brand_profile=brand_profile,
                reference_analysis=reference_analysis,
            )
        except Exception as e:
            if status_message:
                await status_message.edit(content=f"Context building failed: {e}")
            # Refund credits
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.refund_credits(
                    user_id, image_count, "Context building failed"
                )
            return False

        if status_message:
            await status_message.edit(content="Creating optimized prompts...")

        # Step 3: Generate prompts
        try:
            prompts = await self.prompt_architect.create_prompts(
                context_profile=context_profile,
                image_count=image_count,
                variation_style=form_inputs.get("variation_style", "diverse"),
            )
        except Exception as e:
            if status_message:
                await status_message.edit(content=f"Prompt generation failed: {e}")
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.refund_credits(
                    user_id, image_count, "Prompt generation failed"
                )
            return False

        # Update generation record with context and prompts
        async with async_session() as session:
            generation_service = GenerationService(session)
            await generation_service.update_generation_context(
                generation.id, context_profile, prompts
            )

        if status_message:
            await status_message.edit(content="Generating images...")

        # Progress callback
        async def on_progress(completed: int, total: int, status: str):
            if status_message:
                await self.delivery.send_progress_update(
                    status_message, completed, total, status
                )

        # Step 4: Generate images
        platform = form_inputs.get("platform", "instagram_post")
        results = await self.image_generator.generate_batch(
            prompts=prompts,
            platform=platform,
            reference_image=reference_image,
            on_progress=on_progress,
        )

        # Handle partial failures (refund failed credits)
        if results.failed:
            failed_count = len(results.failed)
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.refund_credits(
                    user_id, failed_count, f"Generation partial failure"
                )

        # Get updated user for credits remaining
        async with async_session() as session:
            user_service = UserService(session)
            user = await user_service.get_user(user_id)
            credits_remaining = user.credits if user else 0

            # Update generation record
            generation_service = GenerationService(session)
            await generation_service.mark_generation_completed(
                generation.id,
                success_count=len(results.successful),
                fail_count=len(results.failed),
            )

        # Delete status message before delivery
        if status_message:
            try:
                await status_message.delete()
            except discord.NotFound:
                pass

        # Step 5: Deliver results
        if results.successful:
            await self.delivery.deliver_batch(
                channel=channel,
                results=results,
                generation_id=generation.id,
                user_id=user_id,
                credits_remaining=credits_remaining,
            )
            return True
        else:
            await channel.send(
                f"**Generation #{generation.id} Failed**\n\n"
                f"All {len(results.failed)} images failed to generate.\n"
                f"Credits have been refunded.\n\n"
                f"Error: {results.failed[0].error if results.failed else 'Unknown'}"
            )
            return False
