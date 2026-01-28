# Implementation Plan: Videos Delete

## Step 1: Add Delete Endpoint
Update `src/stoat_ferret/api/routers/videos.py`:

```python
import os
from fastapi import Response

@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    delete_file: bool = Query(default=False, description="Also delete source file"),
    repo: AsyncVideoRepository = Depends(get_repository),
) -> Response:
    """Delete video from library."""
    # Get video first (for file path if needed)
    video = await repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    # Delete from database
    await repo.delete(video_id)

    # Optionally delete file
    if delete_file and os.path.exists(video.path):
        try:
            os.remove(video.path)
        except OSError:
            pass  # Best effort file deletion

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

## Step 2: Add Tests
Add to `tests/test_api/test_videos.py`:

```python
@pytest.mark.api
async def test_delete_video(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
):
    """Delete removes video from database."""
    video = make_test_video()
    await video_repository.add(video)
    
    response = client.delete(f"/api/v1/videos/{video.id}")
    assert response.status_code == 204
    
    assert await video_repository.get(video.id) is None


@pytest.mark.api
def test_delete_video_not_found(client: TestClient):
    """Delete returns 404 for unknown ID."""
    response = client.delete("/api/v1/videos/nonexistent")
    assert response.status_code == 404
```

## Verification
- Delete removes video from database
- Delete with `delete_file=true` removes file
- 404 returned for unknown video