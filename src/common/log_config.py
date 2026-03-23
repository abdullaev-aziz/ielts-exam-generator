"""Shared logging configuration for all IELTS pipeline processes."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured console logging for the IELTS pipeline."""
    fmt = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
