# Conftest Additions for API Testing

## Overview

This document provides concrete fixture code to add for FastAPI endpoint testing. The fixtures integrate with existing session-scoped fixtures (`sample_video_path`, `video_only_path`) and support the dependency injection patterns.

## File Structure

```
tests/
├── conftest.py              # Existing + new shared markers
├── test_api/
│   ├── __init__.py
│   └── conftest.py          # API-specific fixtures (NEW)
└── ...
```

## Additions to tests/conftest.py

Add these markers and fixtures to the existing `conftest.py`:

```python
# Add to existing tests/conftest.py

# New marker for API tests
api = pytest.mark.api


# Helper for creating test Video objects (useful across test modules)
def make_test_video(**kwargs: object) -> Video:
    """Create a test video with default values.

    Can override any field by passing keyword arguments.
    """
    from stoat_ferret.db.models import Video
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1000000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]
```

**Note:** `make_test_video` already exists in `test_repository_contract.py`. Consider moving it to `conftest.py` to share across test modules.

## New File: tests/test_api/conftest.py

Create this file with API-specific fixtures:

```python
"""Pytest fixtures for API endpoint testing."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.repository import InMemoryVideoRepository

if TYPE_CHECKING:
    from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor


@pytest.fixture
def video_repository() -> InMemoryVideoRepository:
    """Provide a fresh in-memory video repository for each test.

    Returns:
        Empty InMemoryVideoRepository instance.
    """
    return InMemoryVideoRepository()


@pytest.fixture
def ffmpeg_executor() -> FakeFFmpegExecutor:
    """Provide a fake FFmpeg executor with no recordings.

    For tests that need specific FFmpeg responses, create a custom
    fixture or load recordings from a file.

    Returns:
        FakeFFmpegExecutor with empty recordings list.
    """
    from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor

    return FakeFFmpegExecutor(recordings=[])


@pytest.fixture
def app(
    video_repository: InMemoryVideoRepository,
    ffmpeg_executor: FakeFFmpegExecutor,
) -> Generator[FastAPI, None, None]:
    """Provide FastAPI app with test dependencies injected.

    This fixture:
    1. Imports the app
    2. Overrides production dependencies with test doubles
    3. Yields the configured app
    4. Cleans up dependency overrides

    Args:
        video_repository: Test repository to inject.
        ffmpeg_executor: Test executor to inject.

    Yields:
        FastAPI application configured for testing.
    """
    from fastapi import FastAPI
    from stoat_ferret.api.app import app as fastapi_app
    from stoat_ferret.api.dependencies import (
        get_video_repository,
        get_ffmpeg_executor,
    )

    # Override dependencies with test doubles
    fastapi_app.dependency_overrides[get_video_repository] = lambda: video_repository
    fastapi_app.dependency_overrides[get_ffmpeg_executor] = lambda: ffmpeg_executor

    yield fastapi_app

    # Clean up
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Provide TestClient for making HTTP requests to the app.

    Uses context manager to ensure proper lifespan event handling.

    Args:
        app: FastAPI application with test dependencies.

    Yields:
        TestClient instance.
    """
    with TestClient(app) as c:
        yield c


# Optional: Fixture for pre-populated repository
@pytest.fixture
def video_repository_with_data(
    video_repository: InMemoryVideoRepository,
) -> InMemoryVideoRepository:
    """Provide repository pre-populated with test videos.

    Useful for tests that need existing data.

    Returns:
        InMemoryVideoRepository with 3 test videos.
    """
    from tests.conftest import make_test_video

    for i in range(3):
        video_repository.add(make_test_video(filename=f"video_{i}.mp4"))
    return video_repository
```

## Fixture for FFmpeg Recordings

For tests needing specific FFmpeg responses:

```python
# tests/test_api/conftest.py (additional fixture)

from pathlib import Path


@pytest.fixture
def ffmpeg_executor_with_probe() -> FakeFFmpegExecutor:
    """Provide FFmpeg executor with probe command recording.

    Loads pre-recorded ffprobe responses for testing
    video metadata extraction.

    Returns:
        FakeFFmpegExecutor loaded with probe recordings.
    """
    from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor

    recordings_path = Path(__file__).parent / "fixtures" / "ffmpeg" / "probe.json"
    return FakeFFmpegExecutor.from_file(recordings_path)
```

**Recording files location:**
```
tests/test_api/
├── conftest.py
└── fixtures/
    └── ffmpeg/
        ├── probe.json
        └── transcode.json
```

## Integration with Session-Scoped Fixtures

For integration tests that need real video files:

```python
# tests/test_api/conftest.py (additional fixture)

@pytest.fixture
def client_with_real_video(
    app: FastAPI,
    sample_video_path: Path,
    video_repository: InMemoryVideoRepository,
) -> Generator[TestClient, None, None]:
    """Provide client with a real video file registered.

    Useful for integration tests that need actual video data.

    Args:
        app: FastAPI app with test dependencies.
        sample_video_path: Session-scoped generated video file.
        video_repository: Test repository.

    Yields:
        TestClient with video registered in repository.
    """
    from tests.conftest import make_test_video

    # Register the sample video in the repository
    video = make_test_video(
        path=str(sample_video_path),
        filename=sample_video_path.name,
    )
    video_repository.add(video)

    with TestClient(app) as c:
        yield c
```

## Fixture Scope Summary

| Fixture | Scope | Description |
|---------|-------|-------------|
| `sample_video_path` | session | Generated test video (existing) |
| `video_only_path` | session | Video without audio (existing) |
| `video_repository` | function | Fresh InMemoryVideoRepository |
| `ffmpeg_executor` | function | Fresh FakeFFmpegExecutor |
| `app` | function | FastAPI app with overrides |
| `client` | function | TestClient instance |

## Usage Examples

### Basic API Test

```python
# tests/test_api/test_videos.py

import pytest
from fastapi.testclient import TestClient
from stoat_ferret.db.repository import InMemoryVideoRepository

pytestmark = pytest.mark.api  # Mark all tests in module


def test_list_videos_empty(
    client: TestClient,
    video_repository: InMemoryVideoRepository,
):
    """GET /videos returns empty list when no videos exist."""
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == {"videos": [], "total": 0}


def test_list_videos_with_data(
    client: TestClient,
    video_repository: InMemoryVideoRepository,
):
    """GET /videos returns all videos."""
    from tests.conftest import make_test_video

    video = make_test_video()
    video_repository.add(video)

    response = client.get("/videos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["videos"][0]["id"] == video.id
```

### Test with Custom FFmpeg Recording

```python
def test_probe_video(
    client: TestClient,
    ffmpeg_executor_with_probe: FakeFFmpegExecutor,
):
    """GET /videos/{id}/probe returns video metadata."""
    # The ffmpeg_executor_with_probe fixture has pre-recorded responses
    response = client.get("/videos/123/probe")
    assert response.status_code == 200
    assert "duration" in response.json()
    ffmpeg_executor_with_probe.assert_all_consumed()
```

### Integration Test with Real Video

```python
@pytest.mark.slow
@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_upload_and_probe_integration(
    client_with_real_video: TestClient,
    sample_video_path: Path,
):
    """Integration test with actual video file."""
    # Test with real video file
    ...
```
