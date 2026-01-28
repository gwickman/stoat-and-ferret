# Implementation Plan: Externalized Settings

## Step 1: Add Dependency
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing
    "pydantic-settings>=2.0",
]
```

## Step 2: Create Settings Module
Create `src/stoat_ferret/api/settings.py`:

```python
"""Application settings with environment variable support."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="STOAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_path: str = Field(
        default="data/stoat.db",
        description="Path to SQLite database file",
    )

    # API Server
    api_host: str = Field(
        default="127.0.0.1",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server port",
    )

    # Development
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
```

Source: `comms/outbox/exploration/pydantic-settings-current/settings-class.md`

## Step 3: Add Tests
Create `tests/test_api/test_settings.py`:

```python
"""Tests for application settings."""

import pytest

from stoat_ferret.api.settings import Settings, get_settings


def test_default_settings():
    """Settings have sensible defaults."""
    settings = Settings()
    assert settings.database_path == "data/stoat.db"
    assert settings.api_port == 8000
    assert settings.debug is False


def test_environment_override(monkeypatch):
    """Environment variables override defaults."""
    monkeypatch.setenv("STOAT_API_PORT", "9000")
    monkeypatch.setenv("STOAT_DEBUG", "true")
    
    # Clear cache to pick up new env vars
    get_settings.cache_clear()
    
    settings = Settings()
    assert settings.api_port == 9000
    assert settings.debug is True


def test_invalid_port_rejected():
    """Invalid port values are rejected."""
    with pytest.raises(ValueError):
        Settings(api_port=70000)


def test_get_settings_cached():
    """get_settings returns cached instance."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
```

Source for test patterns: `comms/outbox/exploration/pydantic-settings-current/testing-patterns.md`

## Verification
- `STOAT_API_PORT=9000 uv run python -m stoat_ferret.api` uses port 9000
- Invalid settings raise clear validation errors