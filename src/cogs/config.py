"""Configuration cog for /config command."""

import discord
from discord.ext import commands
from typing import Optional

from src.models import async_session
from src.services import UserService


# Industry options for brand profile
INDUSTRIES = [
    discord.SelectOption(label="Skincare/Beauty", value="skincare"),
    discord.SelectOption(label="Fashion/Apparel", value="fashion"),
    discord.SelectOption(label="Food/Beverage", value="food"),
    discord.SelectOption(label="Tech/SaaS", value="tech"),
    discord.SelectOption(label="Finance/Fintech", value="finance"),
    discord.SelectOption(label="Fitness/Health", value="fitness"),
    discord.SelectOption(label="Real Estate", value="real_estate"),
    discord.SelectOption(label="E-commerce", value="ecommerce"),
    discord.SelectOption(label="Travel/Hospitality", value="travel"),
    discord.SelectOption(label="Education", value="education"),
    discord.SelectOption(label="Other", value="other"),
]


class BrandProfileModal(discord.ui.Modal):
    """Modal for editing brand profile."""

    def __init__(self, current_profile: Optional[dict] = None):
        super().__init__(title="Edit Brand Profile")
        self.current = current_profile or {}

        self.brand_name = discord.ui.InputText(
            label="Brand/Company Name",
            placeholder="e.g., Glow Skincare",
            default=self.current.get("name", ""),
            required=False,
            max_length=100,
        )
        self.add_item(self.brand_name)

        self.colors = discord.ui.InputText(
            label="Brand Colors",
            placeholder="e.g., #FF5733, soft pink, gold accents",
            default=self.current.get("colors", ""),
            required=False,
            max_length=200,
        )
        self.add_item(self.colors)

        self.style_keywords = discord.ui.InputText(
            label="Style Keywords",
            placeholder="e.g., minimal, luxury, clean, editorial",
            default=self.current.get("style_keywords", ""),
            required=False,
            max_length=300,
        )
        self.add_item(self.style_keywords)

        self.avoid_list = discord.ui.InputText(
            label="Things to Avoid",
            placeholder="e.g., neon colors, cluttered backgrounds, cartoonish",
            default=self.current.get("avoid_list", ""),
            required=False,
            max_length=300,
        )
        self.add_item(self.avoid_list)

    async def callback(self, interaction: discord.Interaction):
        """Save brand profile."""
        async with async_session() as session:
            service = UserService(session)
            await service.save_brand_profile(
                discord_id=interaction.user.id,
                name=self.brand_name.value or None,
                colors=self.colors.value or None,
                style_keywords=self.style_keywords.value or None,
                avoid_list=self.avoid_list.value or None,
            )

        await interaction.response.send_message(
            "Brand profile updated!", ephemeral=True
        )


class IndustrySelectView(discord.ui.View):
    """View for selecting industry."""

    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select your industry...",
        options=INDUSTRIES,
        min_values=1,
        max_values=1,
    )
    async def industry_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your settings!", ephemeral=True
            )
            return

        async with async_session() as session:
            service = UserService(session)
            await service.save_brand_profile(
                discord_id=interaction.user.id,
                industry=select.values[0],
            )

        await interaction.response.send_message(
            f"Industry set to: {select.values[0]}", ephemeral=True
        )
        self.stop()


class ConfigView(discord.ui.View):
    """Main config panel view."""

    def __init__(self, user_id: int, has_profile: bool, profile_enabled: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.has_profile = has_profile
        self.profile_enabled = profile_enabled

        # Update toggle button label
        if has_profile:
            self.toggle_button.label = (
                "Disable Brand Profile" if profile_enabled else "Enable Brand Profile"
            )
            self.toggle_button.style = (
                discord.ButtonStyle.danger
                if profile_enabled
                else discord.ButtonStyle.success
            )

    @discord.ui.button(
        label="Edit Brand Profile", style=discord.ButtonStyle.primary, emoji="📝"
    )
    async def edit_profile(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your settings!", ephemeral=True
            )
            return

        # Get current profile
        async with async_session() as session:
            service = UserService(session)
            profile = await service.get_brand_profile(interaction.user.id)

        current = {}
        if profile:
            current = {
                "name": profile.name,
                "colors": profile.colors,
                "style_keywords": profile.style_keywords,
                "avoid_list": profile.avoid_list,
            }

        modal = BrandProfileModal(current)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Set Industry", style=discord.ButtonStyle.secondary, emoji="🏢"
    )
    async def set_industry(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your settings!", ephemeral=True
            )
            return

        view = IndustrySelectView(interaction.user.id)
        await interaction.response.send_message(
            "Select your industry:", view=view, ephemeral=True
        )

    @discord.ui.button(
        label="Toggle Brand Profile", style=discord.ButtonStyle.secondary, emoji="🔄"
    )
    async def toggle_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your settings!", ephemeral=True
            )
            return

        if not self.has_profile:
            await interaction.response.send_message(
                "You don't have a brand profile yet! Click 'Edit Brand Profile' to create one.",
                ephemeral=True,
            )
            return

        async with async_session() as session:
            service = UserService(session)
            new_state = await service.toggle_brand_profile(interaction.user.id)

        status = "enabled" if new_state else "disabled"
        await interaction.response.send_message(
            f"Brand profile {status}!", ephemeral=True
        )

        # Update button
        self.profile_enabled = new_state
        button.label = "Disable Brand Profile" if new_state else "Enable Brand Profile"
        button.style = (
            discord.ButtonStyle.danger if new_state else discord.ButtonStyle.success
        )
        await interaction.message.edit(view=self)

    @discord.ui.button(
        label="View Stats", style=discord.ButtonStyle.secondary, emoji="📊"
    )
    async def view_stats(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your settings!", ephemeral=True
            )
            return

        async with async_session() as session:
            service = UserService(session)
            user = await service.get_user(interaction.user.id)

        if not user:
            await interaction.response.send_message(
                "No account found!", ephemeral=True
            )
            return

        embed = discord.Embed(title="Your Stats", color=0x87CEEB)
        embed.add_field(name="Credits", value=str(user.credits), inline=True)
        embed.add_field(
            name="Total Used", value=str(user.credits_used_total), inline=True
        )
        embed.add_field(
            name="Subscription", value=user.subscription_tier or "None", inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfigCog(commands.Cog):
    """Cog for user configuration commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(
        name="config",
        description="Manage your brand profile and settings",
    )
    async def config(self, ctx: discord.ApplicationContext):
        """Open settings panel."""
        async with async_session() as session:
            service = UserService(session)
            profile = await service.get_brand_profile(ctx.author.id)

        has_profile = profile is not None
        profile_enabled = profile.enabled if profile else False

        # Build embed
        embed = discord.Embed(
            title="Settings",
            description="Manage your brand profile and preferences",
            color=0x87CEEB,
        )

        if profile:
            embed.add_field(
                name="Brand Profile",
                value=(
                    f"**Name:** {profile.name or 'Not set'}\n"
                    f"**Industry:** {profile.industry or 'Not set'}\n"
                    f"**Status:** {'Enabled' if profile.enabled else 'Disabled'}"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Brand Profile",
                value="Not configured. Create one to get consistent branding across generations!",
                inline=False,
            )

        view = ConfigView(ctx.author.id, has_profile, profile_enabled)
        await ctx.respond(embed=embed, view=view, ephemeral=True)


def setup(bot: commands.Bot):
    """Add cog to bot."""
    bot.add_cog(ConfigCog(bot))
