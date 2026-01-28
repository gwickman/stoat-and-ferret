# FastAPI Integration for pydantic-settings v2

Dependency injection patterns for settings in FastAPI.

## Recommended Pattern: Cached Dependency

Use `functools.lru_cache` for singleton settings:

```python
# src/stoat_ferret/dependencies.py
from functools import lru_cache

from stoat_ferret.config import Settings


@lru_cache
def get_settings() -> Settings:
    """
    Return application settings as a cached singleton.

    Settings are loaded once from environment/files and cached
    for the lifetime of the application.
    """
    return Settings()
```

## Using Settings in Endpoints

```python
# src/stoat_ferret/main.py
from fastapi import Depends, FastAPI

from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings

app = FastAPI()


@app.get('/status')
async def get_status(settings: Settings = Depends(get_settings)):
    """Return application status."""
    return {
        'debug': settings.debug,
        'database': str(settings.database_path),
    }


@app.get('/config')
async def get_config(settings: Settings = Depends(get_settings)):
    """Return non-sensitive configuration."""
    return {
        'api_port': settings.api_port,
        'api_host': settings.api_host,
    }
```

## Using Settings in Routers

```python
# src/stoat_ferret/routers/projects.py
from fastapi import APIRouter, Depends

from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings

router = APIRouter(prefix='/projects', tags=['projects'])


@router.get('/')
async def list_projects(settings: Settings = Depends(get_settings)):
    """List all projects."""
    # Use settings.database_path, etc.
    ...
```

## Using Settings in Lifespan

For application startup/shutdown that needs settings:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()

    # Startup
    print(f'Starting with database: {settings.database_path}')
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    print('Shutting down...')


app = FastAPI(lifespan=lifespan)
```

## Settings in Application Factory

For more complex applications:

```python
# src/stoat_ferret/app.py
from fastapi import FastAPI

from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Create FastAPI application with optional settings override.

    Args:
        settings: Optional settings override for testing.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title='stoat-and-ferret',
        debug=settings.debug,
    )

    # Store settings on app state for access outside dependencies
    app.state.settings = settings

    # Include routers
    from stoat_ferret.routers import projects
    app.include_router(projects.router)

    return app
```

## Testing with Dependency Overrides

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from stoat_ferret.main import app
from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings


def get_test_settings() -> Settings:
    """Return test settings."""
    return Settings(
        database_path=Path(':memory:'),
        debug=True,
        _env_file=None,
    )


@pytest.fixture
def client():
    """Test client with overridden settings."""
    app.dependency_overrides[get_settings] = get_test_settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_status_endpoint(client):
    """Test status endpoint returns debug mode."""
    response = client.get('/status')
    assert response.status_code == 200
    assert response.json()['debug'] is True
```

## Clearing Cache for Tests

If you need to reload settings during tests:

```python
from stoat_ferret.dependencies import get_settings


def test_reload_settings(monkeypatch):
    """Test settings reload after environment change."""
    # Clear the cache
    get_settings.cache_clear()

    monkeypatch.setenv('STOAT_DEBUG', 'true')
    settings = get_settings()
    assert settings.debug is True

    # Clear cache again for next test
    get_settings.cache_clear()
```

## Alternative: Settings as App State

For accessing settings without dependency injection:

```python
from fastapi import FastAPI, Request

app = FastAPI()
app.state.settings = get_settings()


@app.get('/status')
async def status(request: Request):
    """Access settings via request.app.state."""
    settings = request.app.state.settings
    return {'debug': settings.debug}
```

## Type Hints for IDEs

Ensure proper type hints for IDE support:

```python
from typing import Annotated
from fastapi import Depends

from stoat_ferret.config import Settings
from stoat_ferret.dependencies import get_settings

# Type alias for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get('/status')
async def status(settings: SettingsDep):
    """Type-safe settings access."""
    return {'debug': settings.debug}
```

## Key Recommendations

1. **Use `@lru_cache`** on the settings getter for singleton behavior

2. **One settings instance** per application - don't create multiple Settings objects

3. **Use `Depends(get_settings)`** for endpoint access

4. **Use `app.state.settings`** for lifespan/startup access

5. **Use `dependency_overrides`** for testing, not monkeypatching the getter

6. **Clear cache** with `get_settings.cache_clear()` if needed between tests

7. **Create type aliases** (`SettingsDep`) for cleaner endpoint signatures
