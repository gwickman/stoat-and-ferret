"""Tests for logging configuration module."""

from __future__ import annotations

import logging

import structlog

from stoat_ferret.logging import configure_logging


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_with_json_format(self) -> None:
        """Test configuring logging with JSON format."""
        # Reset structlog to avoid state from other tests
        structlog.reset_defaults()

        configure_logging(json_format=True, level=logging.INFO)

        logger = structlog.get_logger("test_json")
        # Should not raise
        logger.info("test message", key="value")

    def test_configure_logging_with_console_format(self) -> None:
        """Test configuring logging with console format."""
        # Reset structlog to avoid state from other tests
        structlog.reset_defaults()

        configure_logging(json_format=False, level=logging.DEBUG)

        logger = structlog.get_logger("test_console")
        # Should not raise
        logger.debug("test debug message")

    def test_configure_logging_sets_level(self) -> None:
        """Test that configure_logging sets the log level."""
        # Reset structlog to avoid state from other tests
        structlog.reset_defaults()

        configure_logging(json_format=True, level=logging.WARNING)

        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_configure_logging_default_level_is_info(self) -> None:
        """Test that default log level is INFO."""
        # Reset structlog to avoid state from other tests
        structlog.reset_defaults()

        configure_logging(json_format=True)

        root = logging.getLogger()
        assert root.level == logging.INFO
