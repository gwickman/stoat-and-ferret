# Implementation Plan: Videos Search

## Step 1: Add Search Schema
Update `src/stoat_ferret/api/schemas/video.py`:

```python
class VideoSearchResponse(BaseModel):
    """Search results response."""
    
    videos: list[VideoResponse]
    total: int
    query: str
```

## Step 2: Add Search Endpoint
Update `src/stoat_ferret/api/routers/videos.py`:

```python
from stoat_ferret.api.schemas.video import VideoSearchResponse

@router.get("/search", response_model=VideoSearchResponse)
async def search_videos(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    repo: AsyncVideoRepository = Depends(get_repository),
) -> VideoSearchResponse:
    """Search videos by filename or path."""
    videos = await repo.search(q, limit=limit)
    
    return VideoSearchResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=len(videos),
        query=q,
    )
```

## Step 3: Add Tests
Add to `tests/test_api/test_videos.py`:

```python
@pytest.mark.api
async def test_search_finds_by_filename(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
):
    """Search finds videos by filename."""
    video = make_test_video(filename="vacation_beach.mp4")
    await video_repository.add(video)
    
    response = client.get("/api/v1/videos/search?q=beach")
    assert response.status_code == 200
    assert len(response.json()["videos"]) == 1
    assert response.json()["query"] == "beach"


@pytest.mark.api
def test_search_no_results(client: TestClient):
    """Search returns empty for no matches."""
    response = client.get("/api/v1/videos/search?q=nonexistent")
    assert response.status_code == 200
    assert response.json()["videos"] == []
```

## Verification
- Search returns matching videos
- Query parameter is required