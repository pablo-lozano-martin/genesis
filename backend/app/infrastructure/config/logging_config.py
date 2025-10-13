# ABOUTME: Logging configuration for the application using Python's logging module
# ABOUTME: Sets up structured logging with configurable log levels based on settings

import logging
import sys
from typing import Any

from app.infrastructure.config.settings import settings


def setup_logging() -> None:
    """Configure application logging based on settings."""

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("genesis")
    logger.setLevel(log_level)

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"genesis.{name}")
