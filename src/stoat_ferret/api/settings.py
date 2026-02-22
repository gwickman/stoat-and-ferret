"""Application settings with environment variable support."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings.

    Settings can be configured via environment variables with STOAT_ prefix,
    a .env file, or direct instantiation.

    Example:
        STOAT_API_PORT=9000 python -m stoat_ferret.api
    """

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

    # Storage
    thumbnail_dir: str = Field(
        default="data/thumbnails",
        description="Directory for storing generated thumbnails",
    )

    # Frontend
    gui_static_path: str = Field(
        default="gui/dist",
        description="Path to GUI static files directory",
    )

    # WebSocket
    ws_heartbeat_interval: int = Field(
        default=30,
        ge=1,
        description="WebSocket heartbeat interval in seconds",
    )

    # Logging
    log_backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of rotated log file backups to keep",
    )
    log_max_bytes: int = Field(
        default=10_485_760,
        ge=0,
        description="Maximum log file size in bytes before rotation (default 10MB)",
    )

    # Security
    allowed_scan_roots: list[str] = Field(
        default_factory=list,
        description="Allowed root directories for scanning. Empty list allows all directories.",
    )

    @property
    def database_path_resolved(self) -> Path:
        """Get database path as a Path object.

        Returns:
            The database path as a Path instance.
        """
        return Path(self.database_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Application settings instance, cached for performance.
    """
    return Settings()
