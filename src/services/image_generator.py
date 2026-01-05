"""Image Generator with parallel processing.

Generates images using Gemini API with load balancing
across multiple accounts and parallel execution.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Callable, Any
from io import BytesIO

from google import genai
from google.genai import types

from src.config import settings
from src.services.load_balancer import get_load_balancer, AccountStatus


@dataclass
class GenerationResult:
    """Result of a single image generation."""

    index: int
    success: bool
    image_data: Optional[bytes] = None
    error: Optional[str] = None
    elapsed: float = 0
    prompt: str = ""


@dataclass
class BatchResult:
    """Result of a batch generation."""

    successful: list[GenerationResult]
    failed: list[GenerationResult]
    total_time: float
    prompts_used: list[str]


# Platform to aspect ratio mapping
PLATFORM_ASPECT_RATIOS = {
    "instagram_post": "1:1",
    "instagram_story": "9:16",
    "facebook_ad": "1:1",
    "linkedin": "1:1",
    "twitter": "16:9",
    "youtube": "16:9",
    "tiktok": "9:16",
    "custom": "1:1",
}


class ImageGenerator:
    """
    Generates images using Gemini API with parallel processing.

    Features:
    - Parallel generation with load balancing
    - Automatic retry on failure
    - Progress callbacks
    - Reference image support
    """

    def __init__(self):
        self.load_balancer = get_load_balancer()
        self.model = settings.gemini_model
        self.max_retries = 3
        self.retry_delay = 5

    async def generate_batch(
        self,
        prompts: list[str],
        platform: str = "instagram_post",
        reference_image: Optional[bytes] = None,
        on_progress: Optional[Callable[[int, int, str], Any]] = None,
    ) -> BatchResult:
        """
        Generate a batch of images in parallel.

        Args:
            prompts: List of text prompts
            platform: Target platform for aspect ratio
            reference_image: Optional reference image bytes
            on_progress: Callback(completed, total, status)

        Returns:
            BatchResult with successful and failed generations
        """
        start_time = time.time()
        total = len(prompts)

        # Get aspect ratio from platform
        aspect_ratio = PLATFORM_ASPECT_RATIOS.get(platform, "1:1")

        # Create tasks for parallel execution
        tasks = []
        for i, prompt in enumerate(prompts):
            task = asyncio.create_task(
                self._generate_single_with_retry(
                    index=i,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    reference_image=reference_image,
                )
            )
            tasks.append(task)

        # Track progress
        successful = []
        failed = []
        completed = 0

        # Process as tasks complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1

            if result.success:
                successful.append(result)
                status = f"Generated image {result.index + 1}"
            else:
                failed.append(result)
                status = f"Failed image {result.index + 1}: {result.error}"

            if on_progress:
                await self._call_progress(on_progress, completed, total, status)

        # Sort by index
        successful.sort(key=lambda x: x.index)
        failed.sort(key=lambda x: x.index)

        return BatchResult(
            successful=successful,
            failed=failed,
            total_time=time.time() - start_time,
            prompts_used=prompts,
        )

    async def _call_progress(
        self,
        callback: Callable,
        completed: int,
        total: int,
        status: str,
    ) -> None:
        """Call progress callback, handling both sync and async."""
        result = callback(completed, total, status)
        if asyncio.iscoroutine(result):
            await result

    async def _generate_single_with_retry(
        self,
        index: int,
        prompt: str,
        aspect_ratio: str,
        reference_image: Optional[bytes] = None,
    ) -> GenerationResult:
        """Generate a single image with retry logic."""
        last_error = None

        for attempt in range(self.max_retries):
            # Acquire account from load balancer
            account = await self.load_balancer.acquire_account(timeout=60)

            if not account:
                last_error = "No available API accounts"
                continue

            try:
                result = await self._generate_single(
                    index=index,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    reference_image=reference_image,
                    api_key=account.api_key,
                )

                # Release account
                await self.load_balancer.release_account(
                    account,
                    success=result.success,
                    rate_limited="rate" in (result.error or "").lower(),
                )

                if result.success:
                    return result

                last_error = result.error

                # Don't retry on certain errors
                if result.error and any(
                    x in result.error.lower()
                    for x in ["safety", "blocked", "invalid"]
                ):
                    break

            except Exception as e:
                await self.load_balancer.release_account(
                    account, success=False, rate_limited="429" in str(e)
                )
                last_error = str(e)

            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return GenerationResult(
            index=index,
            success=False,
            error=last_error or "Unknown error",
            prompt=prompt,
        )

    async def _generate_single(
        self,
        index: int,
        prompt: str,
        aspect_ratio: str,
        reference_image: Optional[bytes],
        api_key: str,
    ) -> GenerationResult:
        """Generate a single image (no retry)."""
        start_time = time.time()

        try:
            # Create client with specific API key
            client = genai.Client(api_key=api_key)

            # Build content parts
            parts = []

            # Add reference image if provided
            if reference_image:
                parts.append(
                    types.Part.from_bytes(data=reference_image, mime_type="image/png")
                )

            # Add prompt text
            parts.append(types.Part.from_text(text=prompt))

            contents = [types.Content(role="user", parts=parts)]

            # Configure generation
            image_config_params = {"image_size": "2K"}
            if aspect_ratio and aspect_ratio != "1:1":
                image_config_params["aspect_ratio"] = aspect_ratio

            generate_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(**image_config_params),
            )

            # Generate
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=contents,
                config=generate_config,
            )

            elapsed = time.time() - start_time

            # Extract image
            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        return GenerationResult(
                            index=index,
                            success=True,
                            image_data=part.inline_data.data,
                            elapsed=elapsed,
                            prompt=prompt,
                        )
                    elif hasattr(part, "text") and part.text:
                        # Model returned text instead of image
                        return GenerationResult(
                            index=index,
                            success=False,
                            error=f"Model returned text: {part.text[:100]}",
                            elapsed=elapsed,
                            prompt=prompt,
                        )

            return GenerationResult(
                index=index,
                success=False,
                error="No image in response",
                elapsed=elapsed,
                prompt=prompt,
            )

        except Exception as e:
            return GenerationResult(
                index=index,
                success=False,
                error=str(e),
                elapsed=time.time() - start_time,
                prompt=prompt,
            )

    async def generate_single(
        self,
        prompt: str,
        platform: str = "instagram_post",
        reference_image: Optional[bytes] = None,
    ) -> GenerationResult:
        """
        Generate a single image.

        Convenience method for generating one image.
        """
        result = await self.generate_batch(
            prompts=[prompt],
            platform=platform,
            reference_image=reference_image,
        )

        if result.successful:
            return result.successful[0]
        elif result.failed:
            return result.failed[0]
        else:
            return GenerationResult(
                index=0, success=False, error="No result", prompt=prompt
            )
