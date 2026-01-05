"""Prompt Architect - Second layer of AI pipeline.

Takes structured JSON context profiles and flattens them into
optimized natural language TEXT prompts for Gemini image generation.
"""

import json
from typing import Optional
import anthropic

from src.config import settings


class PromptArchitect:
    """Converts structured context profiles into optimized text prompts."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def create_prompts(
        self,
        context_profile: dict,
        image_count: int,
        variation_style: str = "diverse",
    ) -> list[str]:
        """
        Generate text prompts from context profile.

        Args:
            context_profile: Structured JSON context from Context Builder
            image_count: Number of images to generate
            variation_style: diverse, subtle, or consistent

        Returns:
            List of optimized text prompts
        """
        # Variation instructions based on style
        variation_instructions = {
            "diverse": """Create DIVERSE variations:
- Each prompt should explore a significantly different interpretation
- Vary the composition, angle, lighting approach, and mood
- Push creative boundaries while staying true to the brief
- Each image should feel like a distinct creative direction""",
            "subtle": """Create SUBTLE variations:
- Keep the core concept very similar across all prompts
- Vary small details like exact colors, minor prop placement, slight angle changes
- Each image should feel like the same shoot with minor adjustments
- Maintain consistency in overall mood and style""",
            "consistent": """Create CONSISTENT variations:
- All prompts should describe nearly identical images
- Only vary randomness elements that the AI will interpret differently
- Maintain exact same composition, lighting, and styling intent
- Each image should feel like the same exact shot""",
        }

        system_prompt = """You are an expert prompt engineer specializing in image generation.

Your task is to transform structured context profiles into highly effective natural language prompts for image generation AI.

Key principles:
1. Use natural, flowing language - not bullet points or structured formats
2. Front-load the most important visual elements
3. Be specific about lighting, composition, and style
4. Include quality markers (professional, 8K, detailed, etc.)
5. Mention what to avoid naturally in the description

Output ONLY a JSON array of prompt strings. No explanation, no markdown."""

        user_prompt = f"""Transform this context profile into {image_count} optimized image generation prompts.

CONTEXT PROFILE:
{json.dumps(context_profile, indent=2)}

VARIATION STYLE:
{variation_instructions.get(variation_style, variation_instructions['diverse'])}

Requirements:
1. Each prompt should be 100-250 words of flowing natural language
2. Start with the main subject and immediate visual impact
3. Layer in lighting, color, composition details
4. End with style/quality markers
5. Naturally incorporate what to avoid (e.g., "clean background without clutter" instead of "avoid: clutter")

Output a JSON array with exactly {image_count} prompt strings:
["prompt 1", "prompt 2", ...]"""

        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=4000,
            temperature=0.3 if variation_style == "diverse" else 0.1,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
        )

        try:
            content = response.content[0].text
            # Clean up any markdown formatting
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            prompts = json.loads(content.strip())

            # Ensure we have the right number
            if len(prompts) < image_count:
                # Duplicate prompts if needed
                while len(prompts) < image_count:
                    prompts.extend(prompts[: image_count - len(prompts)])
            elif len(prompts) > image_count:
                prompts = prompts[:image_count]

            return prompts

        except (json.JSONDecodeError, IndexError):
            # Fallback: create single prompt and duplicate
            fallback = self._build_fallback_prompt(context_profile)
            return [fallback] * image_count

    def _build_fallback_prompt(self, context_profile: dict) -> str:
        """Build a basic text prompt from context profile."""
        parts = []

        # Subject
        subject = context_profile.get("subject", {})
        if subject.get("primary"):
            parts.append(subject["primary"])

        # Scene
        scene = context_profile.get("scene", {})
        if scene.get("environment"):
            parts.append(f"in {scene['environment']}")
        if scene.get("background"):
            parts.append(f"with {scene['background']} background")

        # Lighting
        lighting = context_profile.get("lighting", {})
        if lighting.get("type"):
            parts.append(f"lit with {lighting['type']}")

        # Style
        style = context_profile.get("style", {})
        if style.get("aesthetic"):
            parts.append(f"{style['aesthetic']} style")

        # Colors
        color = context_profile.get("color", {})
        if color.get("palette"):
            parts.append(f"featuring {', '.join(color['palette'][:3])} colors")

        # Technical
        tech = context_profile.get("technical", {})
        if tech.get("camera_specs"):
            parts.append(tech["camera_specs"])

        # Quality markers
        parts.append("professional photography, high-end quality, 8K resolution")

        # Avoid (as negatives in description)
        avoid = context_profile.get("avoid", [])
        if avoid:
            parts.append(f"clean and polished without {', '.join(avoid[:3])}")

        return ". ".join(parts)

    async def optimize_single_prompt(self, raw_prompt: str) -> str:
        """
        Optimize a single user-provided prompt.

        Args:
            raw_prompt: Raw prompt text from user

        Returns:
            Optimized prompt for image generation
        """
        system_prompt = """You are an expert prompt engineer. Optimize this prompt for image generation.

Rules:
1. Expand vague terms into specific visual descriptions
2. Add lighting, composition, and quality markers
3. Keep it natural flowing language
4. Maximum 250 words
5. Output ONLY the optimized prompt, nothing else."""

        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": f"Optimize this prompt:\n\n{raw_prompt}"}],
            system=system_prompt,
        )

        return response.content[0].text.strip()

    def distribute_prompts(
        self,
        base_prompts: list[str],
        total_count: int,
        variation_style: str,
    ) -> list[str]:
        """
        Distribute prompts across requested image count.

        For consistent style: repeat same prompt
        For subtle: rotate through prompts
        For diverse: each gets unique prompt (or repeat if not enough)
        """
        if variation_style == "consistent":
            # Use only the first prompt
            return [base_prompts[0]] * total_count

        if variation_style == "subtle":
            # Rotate through prompts
            result = []
            for i in range(total_count):
                result.append(base_prompts[i % len(base_prompts)])
            return result

        # Diverse: use as many unique prompts as possible
        if len(base_prompts) >= total_count:
            return base_prompts[:total_count]
        else:
            result = base_prompts.copy()
            while len(result) < total_count:
                result.extend(base_prompts[: total_count - len(result)])
            return result
