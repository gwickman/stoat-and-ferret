# Application Settings

**Source:** `src/stoat_ferret/api/settings.py`
**Component:** API Gateway

## Purpose

Pydantic BaseSettings model for application configuration via environment variables, .env files, or direct instantiation. Provides centralized configuration for database, API server, storage, frontend, WebSocket, logging, batch rendering, and security settings.

## Public Interface

### Classes

- `Settings(BaseSettings)`: Configuration model with the following fields:
  - **Database**: `database_path` (default: "data/stoat.db")
  - **API Server**: `api_host` (default: "127.0.0.1"), `api_port` (default: 8765, range 1-65535)
  - **Development**: `debug` (default: False), `log_level` (default: "INFO", one of DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - **Storage**: `thumbnail_dir` (default: "data/thumbnails")
  - **Frontend**: `gui_static_path` (default: "gui/dist")
  - **WebSocket**: `ws_heartbeat_interval` (default: 30, ge 1)
  - **Logging**: `log_backup_count` (default: 5, ge 0), `log_max_bytes` (default: 10485760 = 10MB, ge 0)
  - **Batch rendering**: `batch_parallel_limit` (default: 4, range 1-16), `batch_max_jobs` (default: 20, range 1-100)
  - **Security**: `allowed_scan_roots` (default: [], allows all if empty)

- `database_path_resolved` (property): Returns database path as a Path object

### Functions

- `get_settings() -> Settings`: Returns cached Settings instance via `@lru_cache` decorator

## Key Implementation Details

- **Environment variable prefix**: "STOAT_" (e.g., STOAT_API_PORT=9000)
- **Configuration sources**: Environment variables, .env file (UTF-8 encoded), direct instantiation
- **Case insensitivity**: Environment variables are case-insensitive
- **.env file support**: SettingsConfigDict includes `env_file=".env"` for dotenv support
- **Caching**: `get_settings()` uses `@lru_cache` to avoid repeated instantiation; Settings object is immutable Pydantic model
- **Validation**: Pydantic validates ranges (port 1-65535, batch limits, volume ranges, etc.)

## Dependencies

### Internal Dependencies

None (settings module is standalone)

### External Dependencies

- `pydantic.BaseModel`: Pydantic model base class
- `pydantic.Field`: Field definition for validation
- `pydantic_settings.BaseSettings`: Settings base class with env var support
- `pydantic_settings.SettingsConfigDict`: Configuration dict for settings

## Relationships

- **Used by**: `app.py` (lifespan and create_app), `__main__.py` (main), all routers and services
- **Uses**: None
