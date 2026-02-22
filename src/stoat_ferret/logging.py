"""Structured logging configuration for stoat-ferret.

Provides a centralized logging configuration using structlog with support for
both JSON output (production) and console output (development), plus rotating
file-based logging for persistent log output.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog


def configure_logging(
    json_format: bool = True,
    level: int = logging.INFO,
    log_dir: str | Path = "logs",
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
) -> None:
    """Configure structlog for the application.

    Sets up both stdout and rotating file logging with identical formatting.

    Args:
        json_format: If True, output JSON logs. If False, use console format.
        level: Logging level (default: INFO).
        log_dir: Directory for log files (default: "logs").
        max_bytes: Maximum log file size in bytes before rotation (default: 10MB).
        backup_count: Number of rotated backup files to keep (default: 5).
    """
    shared_processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    root = logging.getLogger()

    # Idempotency: only add a handler if root has no StreamHandler already.
    # Use exact type match to avoid matching subclasses (e.g. pytest's LogCaptureHandler).
    has_stream_handler = any(type(h) is logging.StreamHandler for h in root.handlers)
    if not has_stream_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # File handler: rotating log file for persistent output
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    has_file_handler = any(type(h) is RotatingFileHandler for h in root.handlers)
    if not has_file_handler:
        file_handler = RotatingFileHandler(
            filename=str(log_path / "stoat-ferret.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(level)
