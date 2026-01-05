"""Context Builder - First layer of AI pipeline.

Takes user form inputs and builds a structured JSON context profile
using Claude AI for intelligent expansion and detail generation.
"""

import json
from typing import Optional
import anthropic

from src.config import settings


# Industry prompt libraries (invisible to users, used to enhance prompts)
INDUSTRY_DEFAULTS = {
    "skincare": {
        "lighting": "soft diffused beauty lighting, subtle rim light",
        "color_tendencies": ["white", "soft pink", "gold", "cream", "rose gold"],
        "composition": "product prominent, clean negative space, premium feel",
        "style": "high-end editorial, magazine quality, aspirational",
        "technical": "85mm lens feel, shallow depth of field, crisp product focus",
        "avoid": ["harsh shadows", "neon colors", "cluttered backgrounds", "cheap look"],
    },
    "fashion": {
        "lighting": "editorial fashion lighting, dramatic shadows acceptable",
        "color_tendencies": ["varies by brand", "often neutral with pops of color"],
        "composition": "model-focused or flat lay, editorial angles",
        "style": "high fashion editorial, runway inspired, aspirational",
        "technical": "full body or detail shots, sharp focus on garments",
        "avoid": ["amateur posing", "poor fabric draping", "unflattering angles"],
    },
    "food": {
        "lighting": "natural side lighting, warm tones, appetizing glow",
        "color_tendencies": ["warm", "earthy", "fresh greens", "rich browns"],
        "composition": "45-degree overhead or eye level, styled props",
        "style": "appetizing, fresh, lifestyle oriented",
        "technical": "macro detail on textures, steam/freshness cues",
        "avoid": ["cold lighting", "unappetizing colors", "messy presentation"],
    },
    "tech": {
        "lighting": "clean studio lighting, gradient backgrounds",
        "color_tendencies": ["blue", "white", "dark grey", "accent colors"],
        "composition": "product hero shots, floating/isolated, clean geometry",
        "style": "modern, minimal, premium tech aesthetic",
        "technical": "sharp product renders, reflections, perfect surfaces",
        "avoid": ["busy backgrounds", "dated aesthetics", "low-tech feel"],
    },
    "fitness": {
        "lighting": "dramatic gym lighting or outdoor natural",
        "color_tendencies": ["bold", "energetic", "black", "neon accents"],
        "composition": "action shots, dynamic poses, movement",
        "style": "motivational, powerful, aspirational",
        "technical": "freeze motion, sweat detail, muscle definition",
        "avoid": ["static poses", "poor form", "unflattering angles"],
    },
    "default": {
        "lighting": "professional studio lighting",
        "color_tendencies": ["brand appropriate"],
        "composition": "balanced, focused on subject",
        "style": "professional, polished",
        "technical": "sharp focus, proper exposure",
        "avoid": ["amateur quality", "poor composition"],
    },
}

PLATFORM_SPECS = {
    "instagram_post": {
        "aspect_ratio": "1:1",
        "style_notes": "scroll-stopping, vibrant, thumb-friendly text if any",
        "dimensions": "1080x1080",
    },
    "instagram_story": {
        "aspect_ratio": "9:16",
        "style_notes": "vertical, immersive, swipe-up friendly",
        "dimensions": "1080x1920",
    },
    "facebook_ad": {
        "aspect_ratio": "1:1 or 4:5",
        "style_notes": "clear value prop, minimal text, action-oriented",
        "dimensions": "1080x1080 or 1080x1350",
    },
    "linkedin": {
        "aspect_ratio": "1.91:1 or 1:1",
        "style_notes": "professional, business appropriate, thought leadership",
        "dimensions": "1200x627 or 1080x1080",
    },
    "twitter": {
        "aspect_ratio": "16:9 or 1:1",
        "style_notes": "attention-grabbing, works at small sizes",
        "dimensions": "1200x675 or 1080x1080",
    },
    "youtube": {
        "aspect_ratio": "16:9",
        "style_notes": "bold text, expressive faces work well, high contrast",
        "dimensions": "1280x720",
    },
    "tiktok": {
        "aspect_ratio": "9:16",
        "style_notes": "trend-aware, bold, youth-oriented",
        "dimensions": "1080x1920",
    },
    "custom": {
        "aspect_ratio": "varies",
        "style_notes": "user specified",
        "dimensions": "varies",
    },
}

MOOD_DESCRIPTORS = {
    "luxury": "opulent, premium materials, gold/marble accents, sophisticated elegance",
    "minimal": "clean lines, white space, simple composition, less is more",
    "bold": "strong colors, high contrast, impactful, attention-grabbing",
    "playful": "fun, bright colors, whimsical elements, light-hearted",
    "professional": "corporate, trustworthy, clean, business-appropriate",
    "warm": "cozy, inviting, golden tones, comfortable feeling",
    "energetic": "dynamic, movement, vibrant, action-oriented",
    "calm": "serene, soft colors, peaceful, tranquil",
    "trustworthy": "reliable, stable, blue tones, established feel",
    "edgy": "unconventional, dark, rebellious, avant-garde",
    "natural": "organic, earthy, green, sustainable feeling",
    "futuristic": "tech-forward, neon, holographic, sci-fi inspired",
}


class ContextBuilder:
    """Builds structured context profiles from user inputs using Claude AI."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def build_context(
        self,
        form_inputs: dict,
        brand_profile: Optional[dict] = None,
        reference_analysis: Optional[dict] = None,
    ) -> dict:
        """
        Build a comprehensive context profile from user inputs.

        Args:
            form_inputs: Raw form data from Discord modal
            brand_profile: User's brand profile if enabled
            reference_analysis: Analysis of reference image if provided

        Returns:
            Structured JSON context profile
        """
        # Get industry defaults
        industry = None
        if brand_profile:
            industry = brand_profile.get("industry")
        industry_defaults = INDUSTRY_DEFAULTS.get(industry, INDUSTRY_DEFAULTS["default"])

        # Get platform specs
        platform = form_inputs.get("platform", "custom")
        platform_specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["custom"])

        # Expand mood descriptors
        moods = form_inputs.get("moods", [])
        mood_descriptions = [MOOD_DESCRIPTORS.get(m, m) for m in moods]

        # Build the prompt for Claude
        system_prompt = """You are an expert creative director who transforms marketing briefs into detailed image generation specifications.

Your task is to take user inputs and create a comprehensive, structured context profile that will be used to generate marketing images.

Output ONLY valid JSON. No explanation, no markdown formatting, just the JSON object."""

        user_prompt = f"""Create a detailed context profile for this image generation request:

USER INPUTS:
- Content Type: {form_inputs.get('content_type', 'ad')}
- Platform: {platform}
- Promoting: {form_inputs.get('promoting', 'product')}
- Mood/Feeling: {', '.join(moods)}
- Specific Requirements: {form_inputs.get('requirements', 'None specified')}

PLATFORM SPECIFICATIONS:
{json.dumps(platform_specs, indent=2)}

INDUSTRY DEFAULTS (use as base, user inputs override):
{json.dumps(industry_defaults, indent=2)}

MOOD EXPANDED:
{', '.join(mood_descriptions)}

{'BRAND PROFILE:' + json.dumps(brand_profile, indent=2) if brand_profile else 'No brand profile specified.'}

{'REFERENCE IMAGE ANALYSIS:' + json.dumps(reference_analysis, indent=2) if reference_analysis else 'No reference image.'}

Create a JSON context profile with these fields:
{{
  "subject": {{
    "primary": "main subject description",
    "secondary": "supporting elements",
    "positioning": "how subject is positioned in frame"
  }},
  "scene": {{
    "environment": "setting description",
    "props": ["list", "of", "props"],
    "background": "background description"
  }},
  "lighting": {{
    "type": "lighting style",
    "direction": "light direction",
    "mood": "lighting mood/feeling"
  }},
  "color": {{
    "palette": ["primary", "colors"],
    "temperature": "warm/cool/neutral",
    "saturation": "high/medium/low"
  }},
  "composition": {{
    "framing": "how the shot is framed",
    "perspective": "camera angle/perspective",
    "focal_point": "where eye should go"
  }},
  "style": {{
    "aesthetic": "overall visual style",
    "references": "style references",
    "quality": "quality descriptors"
  }},
  "technical": {{
    "aspect_ratio": "{platform_specs.get('aspect_ratio', '1:1')}",
    "dimensions": "{platform_specs.get('dimensions', '1080x1080')}",
    "camera_specs": "simulated camera settings"
  }},
  "avoid": ["list", "of", "things", "to", "avoid"],
  "emphasis": ["list", "of", "key", "priorities"]
}}

Ensure the output:
1. Prioritizes user explicit requirements above all else
2. Incorporates reference image style if provided
3. Applies brand profile settings if provided
4. Uses industry defaults only where user didn't specify
5. Is optimized for the target platform"""

        # Call Claude
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=2000,
            temperature=0,  # Deterministic output
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=system_prompt,
        )

        # Parse response
        try:
            content = response.content[0].text
            # Clean up any markdown formatting
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            context_profile = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            # Fallback to basic structure
            context_profile = self._build_fallback_context(
                form_inputs, platform_specs, industry_defaults, mood_descriptions
            )

        # Add metadata
        context_profile["_metadata"] = {
            "content_type": form_inputs.get("content_type"),
            "platform": platform,
            "variation_style": form_inputs.get("variation_style", "diverse"),
            "industry": industry,
            "brand_profile_used": brand_profile is not None,
            "reference_used": reference_analysis is not None,
        }

        return context_profile

    def _build_fallback_context(
        self,
        form_inputs: dict,
        platform_specs: dict,
        industry_defaults: dict,
        mood_descriptions: list,
    ) -> dict:
        """Build a basic context profile if Claude fails."""
        return {
            "subject": {
                "primary": form_inputs.get("promoting", "product"),
                "secondary": "supporting elements",
                "positioning": "centered, prominent",
            },
            "scene": {
                "environment": "professional studio",
                "props": [],
                "background": "clean, minimal",
            },
            "lighting": {
                "type": industry_defaults.get("lighting", "studio lighting"),
                "direction": "front-facing with soft fill",
                "mood": ", ".join(form_inputs.get("moods", ["professional"])),
            },
            "color": {
                "palette": industry_defaults.get("color_tendencies", ["neutral"]),
                "temperature": "neutral",
                "saturation": "medium",
            },
            "composition": {
                "framing": industry_defaults.get("composition", "balanced"),
                "perspective": "eye level",
                "focal_point": "main subject",
            },
            "style": {
                "aesthetic": industry_defaults.get("style", "professional"),
                "references": ", ".join(mood_descriptions),
                "quality": "high-end, polished",
            },
            "technical": {
                "aspect_ratio": platform_specs.get("aspect_ratio", "1:1"),
                "dimensions": platform_specs.get("dimensions", "1080x1080"),
                "camera_specs": industry_defaults.get("technical", "professional camera"),
            },
            "avoid": industry_defaults.get("avoid", []),
            "emphasis": ["product clarity", "professional quality"],
        }

    async def analyze_reference_image(self, image_bytes: bytes) -> dict:
        """
        Analyze a reference image using Claude Vision.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Analysis dictionary with style, colors, composition, etc.
        """
        import base64

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=1000,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": """Analyze this reference image for image generation purposes.

Output ONLY valid JSON with this structure:
{
  "style": "overall visual style",
  "colors": ["dominant", "colors"],
  "lighting": "lighting description",
  "composition": "composition style",
  "mood": "emotional feeling",
  "notable_elements": ["key", "visual", "elements"],
  "quality_markers": ["what makes it good"]
}""",
                        },
                    ],
                }
            ],
        )

        try:
            content = response.content[0].text
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            return {
                "style": "referenced",
                "colors": ["from reference"],
                "lighting": "as shown",
                "composition": "similar to reference",
                "mood": "match reference",
                "notable_elements": [],
                "quality_markers": [],
            }
