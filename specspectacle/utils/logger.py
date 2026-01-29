"""
Logger configuration for SpecSpectacle
Uses Rich library for colored, formatted console output
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# Rich console for pretty output
console = Console()

# Log directory
LOG_DIR = Path.home() / ".specspectacle" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file with timestamp
LOG_FILE = LOG_DIR / f'specspectacle_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'


def get_log_level() -> str:
    """Get log level from environment variable."""
    return os.getenv("SPECSPECTACLE_LOG_LEVEL", "INFO").upper()


def setup_logger(name: str = "specspectacle") -> logging.Logger:
    """
    Set up logger with Rich handler for console and file handler for logs.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    log_level = get_log_level()
    logger.setLevel(log_level)

    # Rich handler for console output (colored, formatted)
    console_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False,
    )
    console_handler.setLevel(log_level)
    console_format = logging.Formatter("%(message)s", datefmt="[%X]")
    console_handler.setFormatter(console_format)

    # File handler for persistent logs
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def cleanup_old_logs(keep_last: int = 10):
    """
    Clean up old log files, keeping only the most recent N files.

    Args:
        keep_last: Number of recent log files to keep
    """
    log_files = sorted(
        LOG_DIR.glob("specspectacle_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Delete old logs beyond keep_last
    for old_log in log_files[keep_last:]:
        try:
            old_log.unlink()
        except Exception:
            pass  # Ignore errors during cleanup


# Default logger instance
logger = setup_logger()

# Cleanup old logs on import
cleanup_old_logs()


# Progress tracking utilities
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.status import Status


def create_progress():
    """Create a progress bar for tracking multi-step operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )


def create_spinner(message: str) -> Status:
    """Create a spinner for long-running operations."""
    return console.status(message, spinner="dots")


# Export console for use in CLI commands
__all__ = ["logger", "console", "setup_logger", "create_progress", "create_spinner"]
