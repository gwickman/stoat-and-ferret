# Handoff: 002-externalized-settings

## What Was Implemented

The application now has externalized configuration via pydantic-settings. Settings can be configured through:
1. Environment variables with `STOAT_` prefix (e.g., `STOAT_API_PORT=9000`)
2. A `.env` file in the project root
3. Direct instantiation for testing

## Available Settings

| Setting | Default | Env Variable | Description |
|---------|---------|--------------|-------------|
| `database_path` | `data/stoat.db` | `STOAT_DATABASE_PATH` | SQLite database path |
| `api_host` | `127.0.0.1` | `STOAT_API_HOST` | API server host |
| `api_port` | `8000` | `STOAT_API_PORT` | API server port (1-65535) |
| `debug` | `False` | `STOAT_DEBUG` | Enable debug mode |
| `log_level` | `INFO` | `STOAT_LOG_LEVEL` | Logging level |

## Usage Patterns

### Access settings in code
```python
from stoat_ferret.api.settings import get_settings

settings = get_settings()  # Cached singleton
print(settings.api_port)
```

### Override in tests
```python
from stoat_ferret.api.settings import Settings, get_settings

# Clear cache and set env var
get_settings.cache_clear()
monkeypatch.setenv("STOAT_API_PORT", "9000")
settings = Settings()  # Picks up env var
```

### Database path as Path object
```python
settings = get_settings()
path: Path = settings.database_path_resolved  # Returns Path object
```

## Integration Notes

- The `__main__.py` already uses `settings.api_host` and `settings.api_port` for uvicorn
- The `app.py` lifespan uses `settings.database_path_resolved` for database connection
- The `log_level` and `debug` settings are available but not yet wired to actual logging configuration

## Next Feature Suggestions

1. Wire `log_level` to structlog configuration
2. Wire `debug` to FastAPI debug mode
3. Add settings endpoint (GET /settings) for runtime introspection (sanitized)
