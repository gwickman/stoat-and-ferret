# Theme 02: api-foundation

## Overview

Establish FastAPI application structure with production-ready observability and configuration. This theme creates the foundation for all API endpoints.

## Context

Roadmap milestone M1.6 specifies:
- REST API framework (FastAPI)
- Request correlation ID middleware
- Metrics middleware for all endpoints
- Graceful shutdown handling

Explorations completed:
- `pydantic-settings-current`: Configuration patterns documented
- `fastapi-testing-patterns`: Testing architecture documented
- `aiosqlite-migration`: Lifespan pattern for connections

## Architecture Decisions

### AD-001: Lifespan Pattern for Resources
Use FastAPI lifespan context manager for database connection:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await aiosqlite.connect(settings.database_path)
    yield
    await app.state.db.close()
```

### AD-002: Settings Singleton
Use `@lru_cache` for settings to ensure single instance:
```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### AD-003: Correlation ID via Middleware
Generate UUID at request entry, propagate via contextvars for logging.

## Dependencies
- Theme 1 Feature 1 (async-repository) - For health check database verification
- v002 FFmpegExecutor - For health check FFmpeg verification

## Execution Order
Sequential: 1 → 2 → 3 → 4

## Evidence Sources

| Claim | Source |
|-------|--------|
| pydantic-settings v2 BaseSettings import | `comms/outbox/exploration/pydantic-settings-current/settings-class.md` |
| SettingsConfigDict pattern | `comms/outbox/exploration/pydantic-settings-current/settings-class.md` |
| @lru_cache singleton pattern | `comms/outbox/exploration/pydantic-settings-current/fastapi-integration.md` |
| monkeypatch.setenv for test overrides | `comms/outbox/exploration/pydantic-settings-current/testing-patterns.md` |
| TestClient with dependency_overrides | `comms/outbox/exploration/fastapi-testing-patterns/dependency-injection.md` |
| Lifespan pattern for aiosqlite | `comms/outbox/exploration/aiosqlite-migration/README.md` |

## Success Criteria
- FastAPI app starts with uvicorn
- Settings load from environment/`.env`
- `/health/live` returns 200
- `/health/ready` checks database and FFmpeg
- All requests have correlation ID header
- Prometheus metrics available at `/metrics`