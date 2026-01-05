"""Configuration settings for Mynted bot."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Discord
    discord_token: str

    # Anthropic (Claude)
    anthropic_api_key: str

    # Google (Gemini) - Multiple accounts
    google_api_key_1: str
    google_api_key_2: Optional[str] = None
    google_api_key_3: Optional[str] = None

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Whop
    whop_api_key: Optional[str] = None
    whop_webhook_secret: Optional[str] = None

    # Generation settings
    gemini_model: str = "gemini-2.0-flash-exp"
    claude_model: str = "claude-sonnet-4-20250514"
    max_concurrent_per_account: int = 5
    max_images_per_generation: int = 50

    # Discord settings
    generate_channel_name: str = "generate"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_google_api_keys() -> list[str]:
    """Get all configured Google API keys."""
    keys = [settings.google_api_key_1]
    if settings.google_api_key_2:
        keys.append(settings.google_api_key_2)
    if settings.google_api_key_3:
        keys.append(settings.google_api_key_3)
    return keys
