#!/usr/bin/env python3
"""
Mynted - AI Image Generation Bot
Main entry point for the Discord bot.
"""

import asyncio
import logging

import discord
from discord.ext import commands

from src.config import settings
from src.models import init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mynted")


class MyntedBot(commands.Bot):
    """Custom bot class for Mynted."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="mynted.co",
            ),
        )

        # Store for temporary reference images during generation flow
        self._temp_references: dict[int, bytes] = {}

    async def on_connect(self):
        """Called when bot connects to Discord."""
        logger.info("Initializing database...")
        await init_db()

        logger.info("Loading cogs...")
        # Load cogs
        cog_files = [
            "src.cogs.generate",
            "src.cogs.config",
            "src.cogs.general",
        ]

        for cog in cog_files:
            try:
                self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

        logger.info("Syncing commands...")
        await self.sync_commands()
        logger.info("Commands synced!")

    async def on_ready(self):
        """Called when bot is fully ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info("---")
        logger.info("Mynted bot is ready!")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild."""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")

    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ):
        """Handle command errors."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(
                f"Please wait {error.retry_after:.1f}s before using this command again.",
                ephemeral=True,
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.respond(
                "You don't have permission to use this command.",
                ephemeral=True,
            )
        else:
            logger.error(f"Command error: {error}", exc_info=error)
            await ctx.respond(
                "An error occurred. Please try again later.",
                ephemeral=True,
            )


async def main():
    """Main entry point."""
    logger.info("Starting Mynted bot...")

    bot = MyntedBot()

    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
