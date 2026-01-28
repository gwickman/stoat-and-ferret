# Dependency Injection Override Patterns

## Overview

FastAPI's `app.dependency_overrides` dictionary allows replacing dependencies during tests. This is how we inject test doubles like `InMemoryVideoRepository` and `FakeFFmpegExecutor` into endpoints.

## How Dependency Overrides Work

The `dependency_overrides` dictionary maps:
- **Key**: The original dependency function
- **Value**: The replacement dependency function

FastAPI calls the override instead of the original throughout the application.

```python
# In app
def get_video_repository() -> VideoRepository:
    return SQLiteVideoRepository(db_connection)

# In test
def override_video_repository() -> VideoRepository:
    return InMemoryVideoRepository()

app.dependency_overrides[get_video_repository] = override_video_repository
```

## Pattern 1: Basic Dependency Override

### Production Code

```python
# src/stoat_ferret/api/dependencies.py
from stoat_ferret.db.repository import VideoRepository, SQLiteVideoRepository

def get_video_repository() -> VideoRepository:
    """Production dependency: returns SQLite repository."""
    # In production, this would get a real database connection
    return SQLiteVideoRepository(get_db_connection())
```

### Endpoint Using Dependency

```python
# src/stoat_ferret/api/routes/videos.py
from fastapi import APIRouter, Depends
from stoat_ferret.api.dependencies import get_video_repository
from stoat_ferret.db.repository import VideoRepository

router = APIRouter()

@router.get("/videos")
def list_videos(repo: VideoRepository = Depends(get_video_repository)):
    videos = repo.list_videos()
    return {"videos": videos, "total": len(videos)}
```

### Test with Override

```python
# tests/test_api/test_videos.py
import pytest
from fastapi.testclient import TestClient
from stoat_ferret.api.app import app
from stoat_ferret.api.dependencies import get_video_repository
from stoat_ferret.db.repository import InMemoryVideoRepository

@pytest.fixture
def video_repository() -> InMemoryVideoRepository:
    """Fresh in-memory repository for each test."""
    return InMemoryVideoRepository()

@pytest.fixture
def client(video_repository: InMemoryVideoRepository):
    """TestClient with dependency overrides."""
    def override_repo():
        return video_repository

    app.dependency_overrides[get_video_repository] = override_repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()  # Clean up after test

def test_list_videos_empty(client: TestClient):
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == {"videos": [], "total": 0}
```

## Pattern 2: Multiple Dependencies

### Test Doubles for stoat-and-ferret

The codebase has these test doubles ready:

1. **InMemoryVideoRepository** (`repository.py`)
2. **FakeFFmpegExecutor** (`executor.py`)

### Multiple Override Example

```python
# src/stoat_ferret/api/dependencies.py
from stoat_ferret.db.repository import VideoRepository, SQLiteVideoRepository
from stoat_ferret.ffmpeg.executor import FFmpegExecutor, RealFFmpegExecutor

def get_video_repository() -> VideoRepository:
    return SQLiteVideoRepository(get_db_connection())

def get_ffmpeg_executor() -> FFmpegExecutor:
    return RealFFmpegExecutor()
```

```python
# tests/test_api/conftest.py
import pytest
from fastapi.testclient import TestClient
from stoat_ferret.api.app import app
from stoat_ferret.api.dependencies import get_video_repository, get_ffmpeg_executor
from stoat_ferret.db.repository import InMemoryVideoRepository
from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor

@pytest.fixture
def video_repository() -> InMemoryVideoRepository:
    return InMemoryVideoRepository()

@pytest.fixture
def ffmpeg_executor() -> FakeFFmpegExecutor:
    # Empty recordings for basic tests
    return FakeFFmpegExecutor(recordings=[])

@pytest.fixture
def client(
    video_repository: InMemoryVideoRepository,
    ffmpeg_executor: FakeFFmpegExecutor
):
    """TestClient with all test doubles injected."""
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_ffmpeg_executor] = lambda: ffmpeg_executor

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
```

## Pattern 3: Parameterized Test Doubles

For testing with different repository implementations (like in `test_repository_contract.py`):

```python
@pytest.fixture(params=["memory", "sqlite"])
def video_repository(request, tmp_path):
    """Test with both repository implementations."""
    if request.param == "memory":
        return InMemoryVideoRepository()
    else:
        conn = sqlite3.connect(":memory:")
        create_tables(conn)
        return SQLiteVideoRepository(conn)
```

## Pattern 4: Pre-Configured Test Doubles

### FakeFFmpegExecutor with Recordings

```python
# tests/fixtures/ffmpeg_recordings/probe_video.json
[
    {
        "args": ["-v", "error", "-show_format", "-show_streams", ...],
        "stdin": null,
        "result": {
            "returncode": 0,
            "stdout": "...",
            "stderr": "",
            "duration_seconds": 0.1
        }
    }
]
```

```python
@pytest.fixture
def ffmpeg_executor_with_probe(tmp_path):
    """FakeFFmpegExecutor with probe recording."""
    recordings_path = Path(__file__).parent / "fixtures/ffmpeg_recordings/probe_video.json"
    return FakeFFmpegExecutor.from_file(recordings_path)

def test_probe_video(client: TestClient, ffmpeg_executor_with_probe):
    # Override for this specific test
    app.dependency_overrides[get_ffmpeg_executor] = lambda: ffmpeg_executor_with_probe

    response = client.get("/videos/123/probe")
    assert response.status_code == 200
    ffmpeg_executor_with_probe.assert_all_consumed()
```

## Pattern 5: Override Cleanup

Always clean up overrides to prevent test pollution:

### Option A: Clear All Overrides

```python
@pytest.fixture
def client(video_repository):
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()  # Reset all
```

### Option B: Selective Cleanup

```python
@pytest.fixture
def client(video_repository):
    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = original  # Restore previous state
```

### Option C: Context Manager Pattern

```python
from contextlib import contextmanager

@contextmanager
def override_dependencies(**overrides):
    """Context manager for dependency overrides."""
    original = app.dependency_overrides.copy()
    app.dependency_overrides.update(overrides)
    try:
        yield
    finally:
        app.dependency_overrides = original

# Usage
def test_with_override():
    with override_dependencies(get_video_repository=lambda: InMemoryVideoRepository()):
        client = TestClient(app)
        response = client.get("/videos")
```

## Design Recommendations for stoat-and-ferret

### 1. Centralized Dependencies Module

Create `src/stoat_ferret/api/dependencies.py` with all dependency functions:

```python
"""Dependency injection functions for FastAPI endpoints."""
from stoat_ferret.db.repository import VideoRepository, SQLiteVideoRepository
from stoat_ferret.ffmpeg.executor import FFmpegExecutor, RealFFmpegExecutor

def get_video_repository() -> VideoRepository:
    """Get video repository instance."""
    ...

def get_ffmpeg_executor() -> FFmpegExecutor:
    """Get FFmpeg executor instance."""
    ...
```

### 2. Type Annotations

Use Protocol types in dependencies for proper type checking:

```python
# Dependencies return Protocol types
def get_video_repository() -> VideoRepository:  # Protocol
    return SQLiteVideoRepository(...)  # Concrete implementation
```

### 3. Test Fixture Hierarchy

```
tests/conftest.py           # Shared fixtures (sample_video_path, etc.)
tests/test_api/conftest.py  # API-specific fixtures (client, repositories)
```

### 4. Avoid Global State

Don't use module-level test doubles:

```python
# BAD - global state
_test_repo = InMemoryVideoRepository()
app.dependency_overrides[get_repo] = lambda: _test_repo

# GOOD - fixture-scoped
@pytest.fixture
def video_repository():
    return InMemoryVideoRepository()

@pytest.fixture
def client(video_repository):
    app.dependency_overrides[get_repo] = lambda: video_repository
    ...
```
