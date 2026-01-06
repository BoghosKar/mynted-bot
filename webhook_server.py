"""Standalone webhook server for Whop integration."""

import uvicorn
import logging
from src.services.whop_handler import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("webhook_server")

if __name__ == "__main__":
    logger.info("Starting Whop webhook server on port 8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
