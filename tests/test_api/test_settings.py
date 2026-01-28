"""Tests for application settings."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from stoat_ferret.api.settings import Settings, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_default_settings(self) -> None:
        """Settings have sensible defaults."""
        settings = Settings()
        assert settings.database_path == "data/stoat.db"
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables override defaults."""
        monkeypatch.setenv("STOAT_API_PORT", "9000")
        monkeypatch.setenv("STOAT_DEBUG", "true")
        monkeypatch.setenv("STOAT_DATABASE_PATH", "/custom/path.db")
        monkeypatch.setenv("STOAT_LOG_LEVEL", "DEBUG")

        settings = Settings()
        assert settings.api_port == 9000
        assert settings.debug is True
        assert settings.database_path == "/custom/path.db"
        assert settings.log_level == "DEBUG"

    def test_case_insensitive_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variable names are case insensitive."""
        monkeypatch.setenv("STOAT_API_HOST", "0.0.0.0")

        settings = Settings()
        assert settings.api_host == "0.0.0.0"

    def test_invalid_port_rejected_too_high(self) -> None:
        """Port values above 65535 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=70000)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("api_port",) for e in errors)

    def test_invalid_port_rejected_too_low(self) -> None:
        """Port values below 1 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=0)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("api_port",) for e in errors)

    def test_invalid_log_level_rejected(self) -> None:
        """Invalid log levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(log_level="INVALID")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("log_level",) for e in errors)

    def test_valid_log_levels_accepted(self) -> None:
        """All valid log levels are accepted."""
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            settings = Settings(log_level=level)  # type: ignore[arg-type]
            assert settings.log_level == level

    def test_database_path_resolved_property(self) -> None:
        """database_path_resolved returns a Path object."""
        settings = Settings(database_path="/some/path.db")
        assert isinstance(settings.database_path_resolved, Path)
        assert settings.database_path_resolved == Path("/some/path.db")


class TestGetSettings:
    """Tests for the get_settings function."""

    def test_get_settings_returns_instance(self) -> None:
        """get_settings returns a Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_cached(self) -> None:
        """get_settings returns the same cached instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_can_be_cleared(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clearing cache allows new settings to be loaded."""
        get_settings.cache_clear()
        s1 = get_settings()

        monkeypatch.setenv("STOAT_API_PORT", "3000")
        get_settings.cache_clear()
        s2 = get_settings()

        assert s1 is not s2
        assert s2.api_port == 3000
