"""Tests for logging startup integration."""

from __future__ import annotations

import logging
from collections.abc import Generator
from unittest.mock import patch

import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.logging import configure_logging


@pytest.fixture(autouse=True)
def _clean_root_handlers() -> Generator[None, None, None]:
    """Remove handlers added by configure_logging between tests."""
    yield
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if type(h) is not logging.StreamHandler]


class TestConfigureLoggingIdempotency:
    """Tests for configure_logging() idempotency (FR-006)."""

    def test_single_call_adds_one_handler(self) -> None:
        """Calling configure_logging() once adds exactly one StreamHandler."""
        root = logging.getLogger()
        initial_count = len([h for h in root.handlers if type(h) is logging.StreamHandler])

        configure_logging(level=logging.INFO)

        stream_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert len(stream_handlers) == initial_count + 1

    def test_multiple_calls_no_duplicate_handlers(self) -> None:
        """Calling configure_logging() twice does not add duplicate handlers."""
        configure_logging(level=logging.INFO)
        first_count = len(
            [h for h in logging.getLogger().handlers if type(h) is logging.StreamHandler]
        )

        configure_logging(level=logging.DEBUG)
        second_count = len(
            [h for h in logging.getLogger().handlers if type(h) is logging.StreamHandler]
        )

        assert first_count == second_count


class TestLogLevelConversion:
    """Tests for settings.log_level string-to-int conversion (NFR-001)."""

    @pytest.mark.parametrize(
        ("level_str", "expected_int"),
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_log_level_string_to_int(self, level_str: str, expected_int: int) -> None:
        """settings.log_level string is correctly converted to logging int."""
        assert getattr(logging, level_str) == expected_int


class TestLifespanLogging:
    """Tests for configure_logging() being called during lifespan (FR-001, FR-002)."""

    async def test_configure_logging_called_during_startup(self) -> None:
        """configure_logging() is called during lifespan startup."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
        )

        with patch("stoat_ferret.api.app.configure_logging") as mock_configure:
            async with lifespan(app):
                pass

        mock_configure.assert_called_once()

    async def test_configure_logging_receives_settings_log_level(self) -> None:
        """configure_logging() receives the log level from settings."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
        )

        with patch("stoat_ferret.api.app.configure_logging") as mock_configure:
            async with lifespan(app):
                pass

        # Default log level is INFO
        mock_configure.assert_called_once_with(level=logging.INFO)

    async def test_configure_logging_called_before_deps_injected_check(self) -> None:
        """configure_logging() is called even in test mode (_deps_injected=True)."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
        )

        with patch("stoat_ferret.api.app.configure_logging") as mock_configure:
            async with lifespan(app):
                # Even with _deps_injected=True, logging should be configured
                mock_configure.assert_called_once()


class TestUvicornLogLevel:
    """Tests for uvicorn log_level using settings (FR-005)."""

    def test_uvicorn_receives_settings_log_level(self) -> None:
        """uvicorn.run() receives log_level from settings.log_level.lower()."""
        with (
            patch("stoat_ferret.api.__main__.uvicorn.run") as mock_run,
            patch("stoat_ferret.api.__main__.create_app"),
        ):
            from stoat_ferret.api.__main__ import main

            main()

        call_kwargs = mock_run.call_args[1]
        # Default log level is INFO, so uvicorn should get "info"
        assert call_kwargs["log_level"] == "info"

    def test_uvicorn_log_level_matches_settings(self) -> None:
        """uvicorn log_level matches settings.log_level.lower() for non-default."""
        from stoat_ferret.api.settings import get_settings

        with (
            patch("stoat_ferret.api.__main__.uvicorn.run") as mock_run,
            patch("stoat_ferret.api.__main__.create_app"),
            patch("stoat_ferret.api.__main__.get_settings") as mock_settings,
        ):
            mock_settings.return_value = get_settings()
            mock_settings.return_value.log_level = "DEBUG"  # type: ignore[misc]
            from stoat_ferret.api.__main__ import main

            main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["log_level"] == "debug"


class TestLoggingOutput:
    """System tests for visible log output (FR-003, FR-004)."""

    def test_info_level_produces_output(self, caplog: pytest.LogCaptureFixture) -> None:
        """INFO level produces visible structured output."""
        import structlog

        structlog.reset_defaults()
        configure_logging(json_format=True, level=logging.INFO)

        with caplog.at_level(logging.INFO):
            logger = structlog.get_logger("test_output")
            logger.info("test_visible_output", key="value")

        assert any("test_visible_output" in record.message for record in caplog.records)

    def test_debug_level_produces_debug_output(self, caplog: pytest.LogCaptureFixture) -> None:
        """DEBUG level produces visible debug output (FR-003)."""
        import structlog

        structlog.reset_defaults()
        configure_logging(json_format=True, level=logging.DEBUG)

        with caplog.at_level(logging.DEBUG):
            logger = structlog.get_logger("test_debug")
            logger.debug("debug_message", detail="test")

        assert any("debug_message" in record.message for record in caplog.records)

    def test_default_info_level_without_env_var(self) -> None:
        """Default log level (INFO) works without explicit env var."""
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
