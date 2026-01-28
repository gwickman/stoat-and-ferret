# Implementation Plan: FastAPI App Setup

## Step 1: Add Dependencies
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing
    "fastapi>=0.109",
    "uvicorn[standard]>=0.27",
]

[project.optional-dependencies]
dev = [
    # ... existing
    "httpx>=0.26",
    "pytest-asyncio>=0.23",
]
```

## Step 2: Create API Module Structure
```bash
mkdir -p src/stoat_ferret/api
mkdir -p src/stoat_ferret/api/routers
mkdir -p src/stoat_ferret/api/middleware
mkdir -p src/stoat_ferret/api/schemas
mkdir -p src/stoat_ferret/api/services
touch src/stoat_ferret/api/__init__.py
touch src/stoat_ferret/api/app.py
touch src/stoat_ferret/api/__main__.py
touch src/stoat_ferret/api/routers/__init__.py
touch src/stoat_ferret/api/middleware/__init__.py
touch src/stoat_ferret/api/schemas/__init__.py
touch src/stoat_ferret/api/services/__init__.py
```

## Step 3: Create Test Directory Structure
```bash
mkdir -p tests/test_api
touch tests/test_api/__init__.py
touch tests/test_api/conftest.py
```

## Step 4: Implement Application Factory
Create `src/stoat_ferret/api/app.py`:

```python
"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite
from fastapi import FastAPI

from stoat_ferret.api.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan resources."""
    settings = get_settings()
    
    # Startup: open database connection
    app.state.db = await aiosqlite.connect(settings.database_path)
    app.state.db.row_factory = aiosqlite.Row
    
    yield
    
    # Shutdown: close database connection
    await app.state.db.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="stoat-and-ferret",
        description="AI-driven video editor API",
        version="0.3.0",
        lifespan=lifespan,
    )
    
    # Routers will be added in subsequent features
    
    return app
```

## Step 5: Create Entry Point
Create `src/stoat_ferret/api/__main__.py`:

```python
"""API server entry point."""

import uvicorn

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import get_settings


def main() -> None:
    """Run the API server."""
    settings = get_settings()
    app = create_app()
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
```

## Step 6: Create Shared Test Fixtures
Create `tests/test_api/conftest.py`:

```python
"""Shared fixtures for API tests."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository


@pytest.fixture
def app() -> FastAPI:
    """Create test application."""
    return create_app()


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """In-memory video repository for testing."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Test client for API requests."""
    with TestClient(app) as c:
        yield c
```

## Step 7: Add Basic Tests
Create `tests/test_api/test_app.py`:

```python
"""Tests for FastAPI application."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app


def test_app_creates():
    """Application factory returns FastAPI instance."""
    app = create_app()
    assert app.title == "stoat-and-ferret"
    assert app.version == "0.3.0"


@pytest.mark.api
def test_app_starts(client: TestClient):
    """Application can be started with TestClient."""
    # App started successfully if we get here
    assert client is not None
```

## Verification
- `uv run python -m stoat_ferret.api` starts server
- `curl http://localhost:8000/docs` returns Swagger UI
- `uv run pytest tests/test_api/test_app.py -v` passes