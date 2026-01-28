# Settings Class for stoat-and-ferret

Concrete implementation of externalized configuration for v003.

## Recommended Implementation

```python
"""Application settings with externalized configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_port_range(port: int) -> int:
    """Validate port is in valid range."""
    if not 1 <= port <= 65535:
        raise ValueError(f'Port must be 1-65535, got {port}')
    return port


def validate_path_parent_exists(path: Path) -> Path:
    """Validate parent directory exists (for database path)."""
    if not path.parent.exists():
        raise ValueError(f'Parent directory does not exist: {path.parent}')
    return path


Port = Annotated[int, AfterValidator(validate_port_range)]
DatabasePath = Annotated[Path, AfterValidator(validate_path_parent_exists)]


class Settings(BaseSettings):
    """stoat-and-ferret application settings.

    All settings can be overridden via environment variables with STOAT_ prefix.
    Example: STOAT_DATABASE_PATH=/data/stoat.db

    Settings can also be loaded from a .env file in the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix='STOAT_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        validate_default=True,
    )

    # Database configuration
    database_path: Path = Field(
        default=Path('data/stoat.db'),
        description='Path to SQLite database file',
    )

    # API configuration
    api_host: str = Field(
        default='127.0.0.1',
        description='Host to bind API server',
    )
    api_port: Port = Field(
        default=8000,
        description='Port to bind API server',
    )

    # Debug mode
    debug: bool = Field(
        default=False,
        description='Enable debug mode with verbose logging',
    )

    # FFmpeg configuration
    ffmpeg_path: Path = Field(
        default=Path('ffmpeg'),
        description='Path to FFmpeg executable',
    )

    # Temporary file storage
    temp_dir: Path = Field(
        default=Path('data/temp'),
        description='Directory for temporary files during processing',
    )
```

## Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_DATABASE_PATH` | Path | `data/stoat.db` | SQLite database location |
| `STOAT_API_HOST` | str | `127.0.0.1` | API server host |
| `STOAT_API_PORT` | int | `8000` | API server port (1-65535) |
| `STOAT_DEBUG` | bool | `false` | Debug mode |
| `STOAT_FFMPEG_PATH` | Path | `ffmpeg` | FFmpeg executable |
| `STOAT_TEMP_DIR` | Path | `data/temp` | Temporary file directory |

## Example .env File

```bash
# .env - stoat-and-ferret configuration

STOAT_DATABASE_PATH=data/production.db
STOAT_API_HOST=0.0.0.0
STOAT_API_PORT=8080
STOAT_DEBUG=false
STOAT_FFMPEG_PATH=/usr/bin/ffmpeg
STOAT_TEMP_DIR=/var/tmp/stoat
```

## File Location

Place the Settings class in: `src/stoat_ferret/config.py`

## Usage

```python
from stoat_ferret.config import Settings

# Load from environment and .env
settings = Settings()

# Or override specific values
settings = Settings(api_port=9000)

# Access settings
print(settings.database_path)
print(settings.api_port)
```

## Key Design Decisions

1. **Path type for file paths**: Using `Path` instead of `str` enables path operations and cross-platform compatibility.

2. **Annotated validators**: Using `Annotated[T, AfterValidator(...)]` keeps validation close to the type definition.

3. **validate_default=True**: Ensures default values pass validation (pydantic-settings does this by default, but explicit is better).

4. **Descriptive Field metadata**: Each field has a description for documentation and potential schema generation.

5. **Minimal validation**: Only validate what matters - port range and path existence where needed. Avoid over-validation.
