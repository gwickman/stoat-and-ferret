# Configuration

stoat-and-ferret uses [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for configuration management. All settings can be set via environment variables, a `.env` file, or passed directly in code.

## Environment Variables

All environment variables use the `STOAT_` prefix. The settings class is defined in `src/stoat_ferret/api/settings.py`.

### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_DATABASE_PATH` | `str` | `data/stoat.db` | Path to the SQLite database file. Relative paths are resolved from the working directory. |

### API Server

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_API_HOST` | `str` | `127.0.0.1` | Host address the API server binds to. Use `0.0.0.0` to listen on all interfaces. |
| `STOAT_API_PORT` | `int` | `8000` | Port number for the API server (valid range: 1-65535). |

### Development

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_DEBUG` | `bool` | `false` | Enable debug mode. Accepts `true`, `false`, `1`, `0`, `yes`, `no`. |
| `STOAT_LOG_LEVEL` | `str` | `INFO` | Logging level. One of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

### Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_LOG_BACKUP_COUNT` | `int` | `5` | Number of rotated log file backups to keep (0 = no backups). |
| `STOAT_LOG_MAX_BYTES` | `int` | `10485760` | Maximum log file size in bytes before rotation (default 10 MB, 0 = no rotation). |

### Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_THUMBNAIL_DIR` | `str` | `data/thumbnails` | Directory for storing generated video thumbnails. Created automatically if it does not exist. |

### Frontend

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_GUI_STATIC_PATH` | `str` | `gui/dist` | Path to the built frontend assets directory. The server mounts this directory at `/gui/` and serves it as static files with HTML mode. |

### WebSocket

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_WS_HEARTBEAT_INTERVAL` | `int` | `30` | WebSocket heartbeat interval in seconds (minimum: 1). The server sends periodic pings to keep connections alive. |

### Security

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_ALLOWED_SCAN_ROOTS` | `list[str]` | `[]` (empty) | Allowed root directories for media file scanning. When empty (default), all directories are allowed. Set this to restrict which directories the application can scan for video files. |

To set a list value via environment variable, use a JSON array:

```bash
export STOAT_ALLOWED_SCAN_ROOTS='["/home/user/videos", "/mnt/media"]'
```

## .env File Support

The settings loader automatically reads a `.env` file from the project root if one exists. Variables in `.env` use the same names as environment variables:

```bash
# .env
STOAT_DATABASE_PATH=data/stoat.db
STOAT_API_PORT=9000
STOAT_DEBUG=true
STOAT_LOG_LEVEL=DEBUG
STOAT_THUMBNAIL_DIR=data/thumbnails
STOAT_ALLOWED_SCAN_ROOTS=["/home/user/videos"]
```

The `.env` file uses UTF-8 encoding. Environment variables set in the shell take precedence over values in `.env`.

> **Note:** The `.env` file is not committed to version control. Copy the provided `.env.example` template to get started: `cp .env.example .env`

## pydantic-settings Details

The `Settings` class in `src/stoat_ferret/api/settings.py` extends `BaseSettings` with these behaviors:

- **Prefix:** All environment variables must include the `STOAT_` prefix (e.g., `STOAT_API_PORT`, not `API_PORT`).
- **Case insensitive:** `STOAT_API_PORT` and `stoat_api_port` are treated identically.
- **Caching:** Settings are loaded once and cached via `@lru_cache` on the `get_settings()` function. Changing environment variables after the first access requires a process restart.
- **Validation:** pydantic validates types and constraints at load time. Invalid values (e.g., `STOAT_API_PORT=abc` or `STOAT_API_PORT=99999`) raise a validation error at startup.

Example of overriding settings at startup:

```bash
STOAT_API_PORT=9000 STOAT_DEBUG=true uv run uvicorn stoat_ferret.api.app:create_app --factory --reload
```

## Alembic Configuration

Database migrations are managed by Alembic. The configuration lives in `alembic.ini` at the project root.

| Setting | Value | Description |
|---------|-------|-------------|
| `script_location` | `alembic/` (relative to `alembic.ini`) | Directory containing migration scripts |
| `sqlalchemy.url` | `sqlite:///stoat_ferret.db` | Default database URL for alembic commands |

The `sqlalchemy.url` in `alembic.ini` is used only when running alembic commands directly (e.g., `uv run alembic upgrade head`). The application itself uses `STOAT_DATABASE_PATH` for its runtime database connection.

You can override the alembic database URL on the command line:

```bash
# Use an in-memory database (useful for testing migrations)
uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head

# Use a specific database file
uv run alembic -x sqlalchemy.url=sqlite:///data/stoat.db upgrade head
```

### Common Alembic Commands

```bash
# Apply all migrations (bring database to latest schema)
uv run alembic upgrade head

# Roll back the most recent migration
uv run alembic downgrade -1

# Roll back all migrations
uv run alembic downgrade base

# Show current migration state
uv run alembic current

# Show migration history
uv run alembic history

# Create a new migration (after modifying models)
uv run alembic revision -m "description of change"
```

## Application Endpoints

When the server is running, these endpoints are available:

| Path | Description |
|------|-------------|
| `/api/v1/health/live` | Liveness health check |
| `/api/v1/videos/` | Video management API |
| `/api/v1/projects/` | Project management API |
| `/api/v1/jobs/` | Job queue API |
| `/api/v1/effects/` | Effects registry API |
| `/ws` | WebSocket endpoint for real-time updates |
| `/gui/` | Frontend GUI (served from `STOAT_GUI_STATIC_PATH`) |
| `/metrics` | Prometheus metrics (prometheus-client ASGI app) |
| `/docs` | FastAPI auto-generated Swagger UI |
| `/redoc` | FastAPI auto-generated ReDoc documentation |

## See Also

- [Development Setup](02_development-setup.md) for getting the server running.
- [Troubleshooting](05_troubleshooting.md) for configuration-related issues.
