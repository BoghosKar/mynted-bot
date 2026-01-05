"""Generation cog for /create command."""

import discord
from discord.ext import commands
from discord import SlashCommandGroup
from typing import Optional
import hashlib

from src.config import settings
from src.models import async_session
from src.services import UserService, GenerationService


# Content type options
CONTENT_TYPES = [
    discord.SelectOption(label="Ad", value="ad", description="Advertising creative"),
    discord.SelectOption(label="Product Shot", value="product", description="Product photography style"),
    discord.SelectOption(label="Social Post", value="social", description="Social media post"),
    discord.SelectOption(label="Banner", value="banner", description="Web or display banner"),
    discord.SelectOption(label="Thumbnail", value="thumbnail", description="Video thumbnail"),
    discord.SelectOption(label="Other", value="other", description="Something else"),
]

# Platform options
PLATFORMS = [
    discord.SelectOption(label="Instagram Post", value="instagram_post", description="1:1 square"),
    discord.SelectOption(label="Instagram Story", value="instagram_story", description="9:16 vertical"),
    discord.SelectOption(label="Facebook Ad", value="facebook_ad", description="Various formats"),
    discord.SelectOption(label="LinkedIn", value="linkedin", description="Professional network"),
    discord.SelectOption(label="Twitter/X", value="twitter", description="Tweet image"),
    discord.SelectOption(label="YouTube Thumbnail", value="youtube", description="16:9 landscape"),
    discord.SelectOption(label="TikTok", value="tiktok", description="9:16 vertical"),
    discord.SelectOption(label="Custom", value="custom", description="Specify in requirements"),
]

# Mood options
MOODS = [
    discord.SelectOption(label="Luxury", value="luxury"),
    discord.SelectOption(label="Minimal", value="minimal"),
    discord.SelectOption(label="Bold", value="bold"),
    discord.SelectOption(label="Playful", value="playful"),
    discord.SelectOption(label="Professional", value="professional"),
    discord.SelectOption(label="Warm", value="warm"),
    discord.SelectOption(label="Energetic", value="energetic"),
    discord.SelectOption(label="Calm", value="calm"),
    discord.SelectOption(label="Trustworthy", value="trustworthy"),
    discord.SelectOption(label="Edgy", value="edgy"),
    discord.SelectOption(label="Natural", value="natural"),
    discord.SelectOption(label="Futuristic", value="futuristic"),
]

# Variation styles
VARIATION_STYLES = [
    discord.SelectOption(label="Diverse", value="diverse", description="Maximum variety"),
    discord.SelectOption(label="Subtle", value="subtle", description="Small variations"),
    discord.SelectOption(label="Consistent", value="consistent", description="Very similar"),
]

# Image counts
IMAGE_COUNTS = [
    discord.SelectOption(label="5 images", value="5"),
    discord.SelectOption(label="10 images", value="10"),
    discord.SelectOption(label="20 images", value="20"),
    discord.SelectOption(label="30 images", value="30"),
    discord.SelectOption(label="50 images", value="50"),
]


class GenerationModal(discord.ui.Modal):
    """Modal for text inputs in generation flow."""

    def __init__(self, form_data: dict, has_brand_profile: bool = False):
        super().__init__(title="Create Images")
        self.form_data = form_data
        self.has_brand_profile = has_brand_profile

        # What you're promoting
        self.promoting = discord.ui.InputText(
            label="What are you promoting?",
            placeholder="e.g., A premium skincare serum for anti-aging",
            style=discord.InputTextStyle.paragraph,
            required=True,
            max_length=500,
        )
        self.add_item(self.promoting)

        # Specific requirements
        self.requirements = discord.ui.InputText(
            label="Specific requirements (optional)",
            placeholder="e.g., Include a model, use sunset lighting, show product in hand",
            style=discord.InputTextStyle.paragraph,
            required=False,
            max_length=1000,
        )
        self.add_item(self.requirements)

    async def callback(self, interaction: discord.Interaction):
        """Handle modal submission."""
        self.form_data["promoting"] = self.promoting.value
        self.form_data["requirements"] = self.requirements.value
        self.form_data["use_brand_profile"] = self.has_brand_profile

        # Defer response since generation takes time
        await interaction.response.defer(ephemeral=False)

        # Start generation in the view's callback
        self.form_data["interaction"] = interaction


class Step1View(discord.ui.View):
    """Step 1: Content type and platform selection."""

    def __init__(self, user_id: int, has_brand_profile: bool = False):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.has_brand_profile = has_brand_profile
        self.form_data = {}
        self.completed = False

    @discord.ui.select(
        placeholder="Select content type...",
        options=CONTENT_TYPES,
        min_values=1,
        max_values=1,
    )
    async def content_type_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return
        self.form_data["content_type"] = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Select platform...",
        options=PLATFORMS,
        min_values=1,
        max_values=1,
    )
    async def platform_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return
        self.form_data["platform"] = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Select mood/feeling (max 3)...",
        options=MOODS,
        min_values=1,
        max_values=3,
    )
    async def mood_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return
        self.form_data["moods"] = select.values
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        # Validate required fields
        if "content_type" not in self.form_data:
            await interaction.response.send_message(
                "Please select a content type.", ephemeral=True
            )
            return
        if "platform" not in self.form_data:
            await interaction.response.send_message(
                "Please select a platform.", ephemeral=True
            )
            return
        if "moods" not in self.form_data:
            await interaction.response.send_message(
                "Please select at least one mood.", ephemeral=True
            )
            return

        # Move to step 2
        view = Step2View(self.user_id, self.form_data, self.has_brand_profile)
        await interaction.response.edit_message(
            content="**Step 2/3:** Variation style and image count",
            view=view,
        )
        self.stop()


class Step2View(discord.ui.View):
    """Step 2: Variation style and image count."""

    def __init__(self, user_id: int, form_data: dict, has_brand_profile: bool = False):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.form_data = form_data
        self.has_brand_profile = has_brand_profile

    @discord.ui.select(
        placeholder="Select variation style...",
        options=VARIATION_STYLES,
        min_values=1,
        max_values=1,
    )
    async def variation_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return
        self.form_data["variation_style"] = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="How many images?",
        options=IMAGE_COUNTS,
        min_values=1,
        max_values=1,
    )
    async def count_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return
        self.form_data["image_count"] = int(select.values[0])
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        # Validate
        if "variation_style" not in self.form_data:
            await interaction.response.send_message(
                "Please select a variation style.", ephemeral=True
            )
            return
        if "image_count" not in self.form_data:
            await interaction.response.send_message(
                "Please select image count.", ephemeral=True
            )
            return

        # Show modal for text inputs
        modal = GenerationModal(self.form_data, self.has_brand_profile)
        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def back_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        view = Step1View(self.user_id, self.has_brand_profile)
        view.form_data = {
            k: v
            for k, v in self.form_data.items()
            if k in ["content_type", "platform", "moods"]
        }
        await interaction.response.edit_message(
            content="**Step 1/3:** Select content type, platform, and mood",
            view=view,
        )
        self.stop()


class ReferenceImageView(discord.ui.View):
    """Ask if user wants to add reference image after modal."""

    def __init__(self, user_id: int, form_data: dict, cog: "GenerateCog"):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.form_data = form_data
        self.cog = cog
        self.reference_image: Optional[bytes] = None

    @discord.ui.button(label="Add Reference Image", style=discord.ButtonStyle.primary)
    async def add_reference(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Please upload your reference image now. I'll use it in the next 60 seconds.",
            ephemeral=True,
        )

        # Wait for image upload
        def check(m):
            return (
                m.author.id == self.user_id
                and m.attachments
                and any(
                    a.content_type and a.content_type.startswith("image/")
                    for a in m.attachments
                )
            )

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith(
                    "image/"
                ):
                    self.reference_image = await attachment.read()
                    self.form_data["reference_hash"] = hashlib.sha256(
                        self.reference_image
                    ).hexdigest()[:16]
                    break

            await msg.delete()
            await self.cog.start_generation(
                interaction.message, self.form_data, self.reference_image
            )
        except TimeoutError:
            await self.cog.start_generation(interaction.message, self.form_data, None)

        self.stop()

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip_reference(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        await interaction.response.defer()
        await self.cog.start_generation(interaction.message, self.form_data, None)
        self.stop()


class FeedbackView(discord.ui.View):
    """Feedback buttons for completed generation."""

    def __init__(self, generation_id: int, user_id: int):
        super().__init__(timeout=None)  # Persistent
        self.generation_id = generation_id
        self.user_id = user_id

    @discord.ui.button(label="Amazing", emoji="🔥", style=discord.ButtonStyle.success, custom_id="rate_amazing")
    async def rate_amazing(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self._handle_rating(interaction, "amazing")

    @discord.ui.button(label="Good", emoji="👍", style=discord.ButtonStyle.primary, custom_id="rate_good")
    async def rate_good(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self._handle_rating(interaction, "good")

    @discord.ui.button(label="Okay", emoji="😐", style=discord.ButtonStyle.secondary, custom_id="rate_okay")
    async def rate_okay(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self._handle_rating(interaction, "okay")

    @discord.ui.button(label="Bad", emoji="👎", style=discord.ButtonStyle.danger, custom_id="rate_bad")
    async def rate_bad(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self._handle_rating(interaction, "bad")

    async def _handle_rating(self, interaction: discord.Interaction, rating: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your generation!", ephemeral=True
            )
            return

        async with async_session() as session:
            service = GenerationService(session)
            await service.set_generation_rating(self.generation_id, rating)

        await interaction.response.send_message(
            f"Thanks for rating! Your feedback helps improve future generations.",
            ephemeral=True,
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)


class GenerateCog(commands.Cog):
    """Cog for image generation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(
        name="create",
        description="Generate AI images for your marketing",
    )
    async def create(
        self,
        ctx: discord.ApplicationContext,
        reference: Optional[discord.Attachment] = None,
    ):
        """Start image generation flow."""
        # Check if in correct channel
        if ctx.channel.name != settings.generate_channel_name:
            await ctx.respond(
                f"Please use this command in #{settings.generate_channel_name}",
                ephemeral=True,
            )
            return

        # Check user credits
        async with async_session() as session:
            user_service = UserService(session)
            user = await user_service.get_or_create_user(ctx.author.id)

            if not user.has_credits(1):
                await ctx.respond(
                    "You don't have any credits! Use `/buy` to get more.",
                    ephemeral=True,
                )
                return

            # Check for brand profile
            brand_profile = await user_service.get_brand_profile(ctx.author.id)
            has_brand_profile = brand_profile is not None and brand_profile.enabled

        # Store reference image if provided
        reference_bytes = None
        reference_hash = None
        if reference and reference.content_type.startswith("image/"):
            reference_bytes = await reference.read()
            reference_hash = hashlib.sha256(reference_bytes).hexdigest()[:16]

        # Start step 1
        view = Step1View(ctx.author.id, has_brand_profile)

        if reference_hash:
            view.form_data["reference_hash"] = reference_hash
            # Store reference for later
            self.bot._temp_references = getattr(self.bot, "_temp_references", {})
            self.bot._temp_references[ctx.author.id] = reference_bytes

        await ctx.respond(
            "**Step 1/3:** Select content type, platform, and mood",
            view=view,
        )

    async def start_generation(
        self,
        message: discord.Message,
        form_data: dict,
        reference_image: Optional[bytes],
    ):
        """Start the actual image generation process."""
        from src.services.orchestrator import Orchestrator

        interaction = form_data.pop("interaction", None)
        if not interaction:
            return

        user_id = interaction.user.id
        image_count = form_data.get("image_count", 5)

        # Send initial status message
        status_msg = await interaction.followup.send(
            f"Starting generation of {image_count} images...\n\n"
            "Building context profile..."
        )

        # Run the full pipeline through orchestrator
        orchestrator = Orchestrator()
        await orchestrator.process_generation(
            channel=interaction.channel,
            user_id=user_id,
            form_inputs=form_data,
            reference_image=reference_image,
            status_message=status_msg,
        )


def setup(bot: commands.Bot):
    """Add cog to bot."""
    bot.add_cog(GenerateCog(bot))
