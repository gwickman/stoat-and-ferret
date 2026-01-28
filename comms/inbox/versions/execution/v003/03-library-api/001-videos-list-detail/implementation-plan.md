# Implementation Plan: Videos List and Detail

## Step 1: Create Schemas
Create `src/stoat_ferret/api/schemas/video.py`:

```python
"""Video API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class VideoResponse(BaseModel):
    """Video response schema."""
    
    id: str
    path: str
    filename: str
    duration_frames: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    width: int
    height: int
    video_codec: str
    audio_codec: str | None = None
    file_size: int
    thumbnail_path: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Paginated video list response."""
    
    videos: list[VideoResponse]
    total: int
    limit: int
    offset: int
```

## Step 2: Create Router
Create `src/stoat_ferret/api/routers/videos.py`:

```python
"""Video endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.video import VideoListResponse, VideoResponse
from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository, AsyncVideoRepository

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


async def get_repository(request: Request) -> AsyncVideoRepository:
    """Get video repository from app state."""
    return AsyncSQLiteVideoRepository(request.app.state.db)


@router.get("", response_model=VideoListResponse)
async def list_videos(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: AsyncVideoRepository = Depends(get_repository),
) -> VideoListResponse:
    """List videos with pagination."""
    videos = await repo.list_videos(limit=limit, offset=offset)
    # TODO: Get total count efficiently
    total = len(videos)  # Placeholder
    
    return VideoListResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    repo: AsyncVideoRepository = Depends(get_repository),
) -> VideoResponse:
    """Get video by ID."""
    video = await repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )
    return VideoResponse.model_validate(video)
```

## Step 3: Register Router
Update `src/stoat_ferret/api/app.py`:

```python
from stoat_ferret.api.routers import health, videos

def create_app() -> FastAPI:
    # ... existing
    app.include_router(videos.router)
    return app
```

## Step 4: Update Test Fixtures
Update `tests/test_api/conftest.py` to include video repository override:

```python
from stoat_ferret.api.routers.videos import get_repository as get_video_repository

@pytest.fixture
def client(
    app: FastAPI,
    video_repository: AsyncInMemoryVideoRepository,
) -> Generator[TestClient, None, None]:
    """Test client with dependency overrides."""
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()
```

## Step 5: Add Tests
Create `tests/test_api/test_videos.py`:

```python
"""Tests for video endpoints."""

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.test_repository_contract import make_test_video


@pytest.mark.api
def test_list_videos_empty(client: TestClient):
    """List returns empty when no videos."""
    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    assert response.json()["videos"] == []
    assert response.json()["total"] == 0


@pytest.mark.api
async def test_list_videos_with_data(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
):
    """List returns videos when present."""
    video = make_test_video()
    await video_repository.add(video)
    
    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    assert len(response.json()["videos"]) == 1


@pytest.mark.api
def test_get_video_not_found(client: TestClient):
    """Get returns 404 for unknown ID."""
    response = client.get("/api/v1/videos/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_get_video_found(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
):
    """Get returns video when found."""
    video = make_test_video()
    await video_repository.add(video)
    
    response = client.get(f"/api/v1/videos/{video.id}")
    assert response.status_code == 200
    assert response.json()["id"] == video.id
```

## Verification
- `curl http://localhost:8000/api/v1/videos` returns list
- `curl http://localhost:8000/api/v1/videos/{id}` returns video or 404