"""Logging configuration for the ADO AI CLI application."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


console = Console()


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_file_logging: bool = False,
) -> logging.Logger:
    """
    Configure logging with Rich handler for beautiful terminal output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_file_logging: Whether to enable file logging

    Returns:
        Configured logger instance
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("ado_ai_cli")
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with Rich formatting
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        show_time=True,
        show_path=False,
    )
    rich_handler.setLevel(numeric_level)
    rich_formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]",
    )
    rich_handler.setFormatter(rich_formatter)
    logger.addHandler(rich_handler)

    # File handler for persistent logs (optional)
    if enable_file_logging:
        if log_file is None:
            log_file = Path("ado-ai.log")

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger() -> logging.Logger:
    """
    Get the application logger.

    Returns:
        Application logger instance
    """
    return logging.getLogger("ado_ai_cli")
