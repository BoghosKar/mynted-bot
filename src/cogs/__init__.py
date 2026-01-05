"""Discord bot cogs."""

from .generate import GenerateCog
from .config import ConfigCog
from .general import GeneralCog

__all__ = ["GenerateCog", "ConfigCog", "GeneralCog"]
