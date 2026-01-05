"""Delivery service for sending generated images to Discord.

Handles:
- Direct image sending to Discord
- ZIP file creation for bulk downloads
- Progress updates
- Feedback button attachment
"""

import io
import zipfile
import discord
from typing import Optional
from datetime import datetime

from src.services.image_generator import GenerationResult, BatchResult


class DeliveryService:
    """Handles delivery of generated images to Discord."""

    MAX_IMAGES_PER_MESSAGE = 10
    MAX_FILE_SIZE_MB = 50  # Server Boost Level 2

    async def deliver_batch(
        self,
        channel: discord.TextChannel,
        results: BatchResult,
        generation_id: int,
        user_id: int,
        credits_remaining: int,
    ) -> discord.Message:
        """
        Deliver a batch of generated images to Discord.

        Args:
            channel: Discord channel to send to
            results: BatchResult from image generator
            generation_id: Database generation ID
            user_id: Discord user ID for feedback buttons
            credits_remaining: User's remaining credits

        Returns:
            The summary message with feedback buttons
        """
        successful = results.successful
        total_images = len(successful)

        if total_images == 0:
            # All failed
            return await channel.send(
                f"**Generation #{generation_id} Failed**\n\n"
                f"All {len(results.failed)} images failed to generate.\n"
                f"Credits have been refunded.\n\n"
                f"Error: {results.failed[0].error if results.failed else 'Unknown'}"
            )

        # Send images in batches of 10
        image_messages = []
        for i in range(0, total_images, self.MAX_IMAGES_PER_MESSAGE):
            batch = successful[i : i + self.MAX_IMAGES_PER_MESSAGE]
            files = []

            for result in batch:
                file = discord.File(
                    io.BytesIO(result.image_data),
                    filename=f"image_{result.index + 1:03d}.png",
                )
                files.append(file)

            msg = await channel.send(files=files)
            image_messages.append(msg)

        # Create ZIP file
        zip_buffer = await self._create_zip(successful, generation_id)

        # Build summary message
        summary = self._build_summary(
            generation_id=generation_id,
            success_count=len(successful),
            fail_count=len(results.failed),
            credits_remaining=credits_remaining,
            total_time=results.total_time,
        )

        # Import here to avoid circular imports
        from src.cogs.generate import FeedbackView

        # Send summary with ZIP and feedback buttons
        view = FeedbackView(generation_id=generation_id, user_id=user_id)

        zip_file = discord.File(
            io.BytesIO(zip_buffer.getvalue()),
            filename=f"mynted_generation_{generation_id}.zip",
        )

        summary_msg = await channel.send(
            content=summary,
            file=zip_file,
            view=view,
        )

        return summary_msg

    async def _create_zip(
        self, results: list[GenerationResult], generation_id: int
    ) -> io.BytesIO:
        """Create a ZIP file containing all generated images."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for result in results:
                if result.image_data:
                    filename = f"image_{result.index + 1:03d}.png"
                    zf.writestr(filename, result.image_data)

            # Add a readme
            readme = self._create_readme(generation_id, len(results))
            zf.writestr("README.txt", readme)

        zip_buffer.seek(0)
        return zip_buffer

    def _create_readme(self, generation_id: int, image_count: int) -> str:
        """Create README content for ZIP file."""
        return f"""Mynted Generation #{generation_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Images: {image_count}

https://mynted.co
Fresh creatives. Instantly.
"""

    def _build_summary(
        self,
        generation_id: int,
        success_count: int,
        fail_count: int,
        credits_remaining: int,
        total_time: float,
    ) -> str:
        """Build summary message text."""
        total = success_count + fail_count
        avg_time = total_time / max(success_count, 1)

        lines = [
            f"**Generation #{generation_id} Complete**",
            "",
            f"Generated {success_count}/{total} images",
        ]

        if fail_count > 0:
            lines.append(f"({fail_count} failed - credits refunded)")

        lines.extend(
            [
                f"Credits remaining: {credits_remaining}",
                f"Time: {total_time:.1f}s (avg {avg_time:.1f}s/image)",
                "",
                "**Rate this generation:**",
            ]
        )

        return "\n".join(lines)

    async def send_progress_update(
        self,
        message: discord.Message,
        completed: int,
        total: int,
        status: str,
    ) -> None:
        """Update a message with generation progress."""
        progress_bar = self._create_progress_bar(completed, total)

        await message.edit(
            content=(
                f"**Generating images...**\n\n"
                f"{progress_bar} {completed}/{total}\n\n"
                f"{status}"
            )
        )

    def _create_progress_bar(self, completed: int, total: int, width: int = 20) -> str:
        """Create a text-based progress bar."""
        filled = int(width * completed / total)
        empty = width - filled
        return f"[{'=' * filled}{' ' * empty}]"

    async def deliver_partial_refund(
        self,
        channel: discord.TextChannel,
        generation_id: int,
        failed_count: int,
        refunded_credits: int,
    ) -> discord.Message:
        """Send notification about partial refund for failed images."""
        return await channel.send(
            f"**Partial Refund**\n\n"
            f"Generation #{generation_id}: {failed_count} images failed.\n"
            f"Refunded {refunded_credits} credits to your account."
        )


# Split ZIP if too large
class ZipSplitter:
    """Utility to split large ZIP files."""

    MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

    @staticmethod
    async def split_if_needed(
        results: list[GenerationResult],
        generation_id: int,
    ) -> list[io.BytesIO]:
        """
        Split results into multiple ZIP files if needed.

        Returns list of ZIP buffers.
        """
        # Estimate size
        total_size = sum(len(r.image_data or b"") for r in results)

        if total_size < ZipSplitter.MAX_SIZE_BYTES * 0.9:
            # Single ZIP is fine
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for result in results:
                    if result.image_data:
                        zf.writestr(
                            f"image_{result.index + 1:03d}.png",
                            result.image_data,
                        )
            buffer.seek(0)
            return [buffer]

        # Need to split
        zips = []
        current_zip = io.BytesIO()
        current_zf = zipfile.ZipFile(current_zip, "w", zipfile.ZIP_DEFLATED)
        current_size = 0
        part = 1

        for result in results:
            if not result.image_data:
                continue

            image_size = len(result.image_data)

            # Check if need new ZIP
            if current_size + image_size > ZipSplitter.MAX_SIZE_BYTES * 0.9:
                current_zf.close()
                current_zip.seek(0)
                zips.append(current_zip)

                part += 1
                current_zip = io.BytesIO()
                current_zf = zipfile.ZipFile(current_zip, "w", zipfile.ZIP_DEFLATED)
                current_size = 0

            current_zf.writestr(
                f"image_{result.index + 1:03d}.png",
                result.image_data,
            )
            current_size += image_size

        # Close last ZIP
        current_zf.close()
        current_zip.seek(0)
        zips.append(current_zip)

        return zips
