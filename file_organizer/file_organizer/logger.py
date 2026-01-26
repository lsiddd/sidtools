"""Logging configuration for file_organizer."""

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_logger: logging.Logger | None = None


def setup_logger(level: LogLevel = "INFO") -> logging.Logger:
    """Configure and return the application logger.

    Args:
        level: The logging level to use.

    Returns:
        Configured logger instance.
    """
    global _logger

    if _logger is not None:
        return _logger

    _logger = logging.getLogger("file_organizer")
    _logger.setLevel(getattr(logging, level))

    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level))
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        _logger.addHandler(handler)

    return _logger


def get_logger() -> logging.Logger:
    """Get the application logger, initializing if necessary.

    Returns:
        The application logger instance.
    """
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


def log_action(message: str, dry_run: bool = False) -> None:
    """Log an action with optional dry-run prefix.

    Args:
        message: The message to log.
        dry_run: If True, prefix message with "DRY RUN: ".
    """
    logger = get_logger()
    if dry_run:
        logger.info(f"DRY RUN: {message}")
    else:
        logger.info(message)


def log_warning(message: str) -> None:
    """Log a warning message.

    Args:
        message: The warning message to log.
    """
    logger = get_logger()
    logger.warning(f"Warning: {message}")


def log_error(message: str) -> None:
    """Log an error message.

    Args:
        message: The error message to log.
    """
    logger = get_logger()
    logger.error(f"Error: {message}")


def log_debug(message: str) -> None:
    """Log a debug message.

    Args:
        message: The debug message to log.
    """
    logger = get_logger()
    logger.debug(message)
