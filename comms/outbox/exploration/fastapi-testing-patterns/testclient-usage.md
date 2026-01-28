# TestClient Usage Patterns

## Overview

FastAPI's `TestClient` is built on Starlette's TestClient, which uses HTTPX internally. It allows testing FastAPI applications without running a server.

## Sync vs Async Testing

### Synchronous Tests (Recommended Default)

Use regular `def` test functions with `TestClient`. This is simpler and works seamlessly with pytest:

```python
from fastapi.testclient import TestClient
from stoat_ferret.api.app import app

client = TestClient(app)

def test_read_videos():
    """Test functions should NOT be async def."""
    response = client.get("/videos")
    assert response.status_code == 200
```

**Key points:**
- Test functions use regular `def`, not `async def`
- No `await` needed when calling client methods
- Works with standard pytest without special configuration

### Asynchronous Tests (When Needed)

Use `httpx.AsyncClient` when you need to test async operations directly (e.g., async database queries within tests):

```python
import pytest
from httpx import ASGITransport, AsyncClient
from stoat_ferret.api.app import app

@pytest.mark.anyio
async def test_async_operation():
    """Use @pytest.mark.anyio for async tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/videos")
    assert response.status_code == 200
```

**When to use async tests:**
- Testing async database operations within the test itself
- Testing WebSocket connections
- When test logic requires `await`

**When NOT to use async tests:**
- Standard HTTP endpoint testing (use sync TestClient)
- Most unit tests (use sync TestClient)

## TestClient Patterns

### Basic GET Request

```python
def test_get_video(client: TestClient):
    response = client.get("/videos/123")
    assert response.status_code == 200
    assert response.json()["id"] == "123"
```

### GET with Query Parameters

```python
def test_list_videos_with_pagination(client: TestClient):
    response = client.get("/videos", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()["videos"]) <= 10
```

### POST with JSON Body

```python
def test_create_video(client: TestClient):
    response = client.post(
        "/videos",
        json={
            "path": "/videos/test.mp4",
            "filename": "test.mp4",
        }
    )
    assert response.status_code == 201
    assert "id" in response.json()
```

### Request with Headers

```python
def test_authenticated_endpoint(client: TestClient):
    response = client.get(
        "/videos",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
```

### File Upload

```python
def test_upload_video(client: TestClient, sample_video_path: Path):
    with open(sample_video_path, "rb") as f:
        response = client.post(
            "/videos/upload",
            files={"file": ("test.mp4", f, "video/mp4")}
        )
    assert response.status_code == 201
```

### Testing Error Responses

```python
def test_video_not_found(client: TestClient):
    response = client.get("/videos/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Video not found"}

def test_validation_error(client: TestClient):
    response = client.post("/videos", json={"invalid": "data"})
    assert response.status_code == 422  # Validation error
```

## TestClient Lifecycle

### Per-Test Client (Recommended)

Use a fixture that creates a fresh client for each test:

```python
@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

### Client as Context Manager

The context manager form ensures proper cleanup of lifespan events:

```python
def test_with_context_manager():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
    # Cleanup happens here
```

### Lifespan Events

TestClient handles startup/shutdown lifespan events when used as a context manager:

```python
@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # startup events run here
    with TestClient(app) as c:
        yield c
    # shutdown events run here
```

## Testing Patterns for stoat-and-ferret

### Pattern 1: Testing with In-Memory Repository

```python
def test_list_videos_empty(client: TestClient, video_repository: InMemoryVideoRepository):
    """Repository is empty by default."""
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json()["videos"] == []

def test_list_videos_with_data(
    client: TestClient,
    video_repository: InMemoryVideoRepository
):
    """Pre-populate repository for test."""
    video = make_test_video()
    video_repository.add(video)

    response = client.get("/videos")
    assert response.status_code == 200
    assert len(response.json()["videos"]) == 1
```

### Pattern 2: Testing FFmpeg Operations with Fake Executor

```python
def test_transcode_video(
    client: TestClient,
    ffmpeg_executor: FakeFFmpegExecutor
):
    """FFmpeg operations use recorded responses."""
    response = client.post("/videos/123/transcode", json={"format": "mp4"})
    assert response.status_code == 202
    ffmpeg_executor.assert_all_consumed()
```

### Pattern 3: Integration Test with Real Video File

```python
@pytest.mark.slow
def test_probe_video_integration(
    client: TestClient,
    sample_video_path: Path
):
    """Integration test with actual video file."""
    # Copy sample video to test location
    # Make request
    # Verify response
```

## Common Pitfalls

### 1. Using `async def` with TestClient

```python
# WRONG - TestClient doesn't work in async functions
async def test_wrong():
    response = client.get("/")  # Will fail

# CORRECT - Use regular def
def test_correct():
    response = client.get("/")
```

### 2. Forgetting Context Manager

```python
# WRONG - Lifespan events may not run
client = TestClient(app)
response = client.get("/")

# CORRECT - Use context manager
with TestClient(app) as client:
    response = client.get("/")
```

### 3. Not Resetting State Between Tests

```python
# WRONG - State leaks between tests
video_repo = InMemoryVideoRepository()

def test_one():
    video_repo.add(video)  # Adds to shared state

def test_two():
    # video_repo still has data from test_one!

# CORRECT - Use fixture for isolation
@pytest.fixture
def video_repository():
    return InMemoryVideoRepository()  # Fresh for each test
```
