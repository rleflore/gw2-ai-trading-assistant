"""Logging configuration."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("gw2trading")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
