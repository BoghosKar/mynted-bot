"""General commands cog."""

import discord
from discord.ext import commands
from datetime import datetime

from src.models import async_session
from src.services import UserService, GenerationService


class GeneralCog(commands.Cog):
    """Cog for general utility commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(
        name="balance",
        description="Check your credit balance",
    )
    async def balance(self, ctx: discord.ApplicationContext):
        """Check credit balance."""
        async with async_session() as session:
            service = UserService(session)
            user = await service.get_or_create_user(ctx.author.id)

        embed = discord.Embed(
            title="Credit Balance",
            color=0x87CEEB,
        )
        embed.add_field(name="Available Credits", value=str(user.credits), inline=True)
        embed.add_field(
            name="Total Used", value=str(user.credits_used_total), inline=True
        )

        if user.subscription_tier:
            embed.add_field(
                name="Subscription", value=user.subscription_tier.title(), inline=True
            )
        else:
            embed.set_footer(text="No active subscription. Use /buy to get credits!")

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(
        name="buy",
        description="Get more credits",
    )
    async def buy(self, ctx: discord.ApplicationContext):
        """Show purchase options."""
        embed = discord.Embed(
            title="💳 Get Mynted AI Credits",
            description="Purchase credits to generate stunning AI images in Discord!",
            color=0x5865F2,
        )

        embed.add_field(
            name="🎯 Starter Pack - $9.99",
            value="**50 credits**\nPerfect for trying out Mynted AI",
            inline=False,
        )
        embed.add_field(
            name="🎨 Creator Pack - $29.99",
            value="**200 credits**\nGreat for regular creators\n*Most Popular!*",
            inline=False,
        )
        embed.add_field(
            name="💼 Professional Pack - $59.99",
            value="**500 credits**\nFor serious professionals\n*Best Value!*",
            inline=False,
        )
        embed.add_field(
            name="🚀 Enterprise Pack - $199.99",
            value="**2000 credits**\nMaximum value for power users",
            inline=False,
        )

        embed.add_field(
            name="",
            value=(
                "**[🛒 Buy Credits on Whop](https://whop.com/hub/biz_7iDflJsY9KDdBY/)**\n\n"
                "✅ Instant delivery after purchase\n"
                "✅ Credits never expire\n"
                "✅ Secure payment via Whop"
            ),
            inline=False,
        )

        embed.set_footer(text="1 credit = 1 AI-generated image | Powered by Claude & Gemini")

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(
        name="history",
        description="View your recent generations",
    )
    async def history(self, ctx: discord.ApplicationContext):
        """Show generation history."""
        async with async_session() as session:
            service = GenerationService(session)
            generations = await service.get_user_history(ctx.author.id, limit=10)

        if not generations:
            await ctx.respond(
                "No generations yet! Use `/create` to get started.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Recent Generations",
            color=0x87CEEB,
        )

        for gen in generations:
            # Format time
            time_str = gen.created_at.strftime("%m/%d %H:%M")

            # Status
            if gen.completed_at:
                status = f"✓ {gen.images_generated}/{gen.image_count}"
            else:
                status = "⏳ In progress"

            # Rating
            rating_emoji = {
                "amazing": "🔥",
                "good": "👍",
                "okay": "😐",
                "bad": "👎",
            }.get(gen.rating, "")

            embed.add_field(
                name=f"#{gen.id} - {time_str}",
                value=(
                    f"**Type:** {gen.content_type or 'N/A'}\n"
                    f"**Platform:** {gen.platform or 'N/A'}\n"
                    f"**Status:** {status} {rating_emoji}"
                ),
                inline=True,
            )

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(
        name="help",
        description="Learn how to use Mynted",
    )
    async def help(self, ctx: discord.ApplicationContext):
        """Show help information."""
        embed = discord.Embed(
            title="Mynted - AI Image Generation",
            description="Create stunning marketing images with AI",
            color=0x87CEEB,
        )

        embed.add_field(
            name="Getting Started",
            value=(
                "1. Use `/buy` to get credits\n"
                "2. Go to #generate channel\n"
                "3. Run `/create` to generate images\n"
                "4. Rate your results to help us improve!"
            ),
            inline=False,
        )

        embed.add_field(
            name="Commands",
            value=(
                "`/create` - Generate AI images\n"
                "`/config` - Set up your brand profile\n"
                "`/balance` - Check your credits\n"
                "`/buy` - Get more credits\n"
                "`/history` - View past generations"
            ),
            inline=False,
        )

        embed.add_field(
            name="Tips",
            value=(
                "• Set up a brand profile for consistent results\n"
                "• Add reference images for better accuracy\n"
                "• Use 'Diverse' variation for exploring ideas\n"
                "• Use 'Consistent' when you know what you want"
            ),
            inline=False,
        )

        embed.set_footer(text="mynted.co | Fresh creatives. Instantly.")

        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    """Add cog to bot."""
    bot.add_cog(GeneralCog(bot))
