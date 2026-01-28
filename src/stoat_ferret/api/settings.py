"""API settings configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


class Settings:
    """Application settings.

    Configure via environment variables or direct instantiation.
    """

    def __init__(
        self,
        api_host: str = "127.0.0.1",
        api_port: int = 8000,
        database_path: str | Path = "stoat_ferret.db",
    ) -> None:
        """Initialize settings.

        Args:
            api_host: Host address to bind the API server.
            api_port: Port number for the API server.
            database_path: Path to the SQLite database file.
        """
        self.api_host = api_host
        self.api_port = api_port
        self.database_path = Path(database_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Application settings instance.
    """
    return Settings()
