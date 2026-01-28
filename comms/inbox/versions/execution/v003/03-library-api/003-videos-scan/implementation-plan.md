# Implementation Plan: Videos Scan

## Step 1: Create Scan Schemas
Update `src/stoat_ferret/api/schemas/video.py`:

```python
class ScanRequest(BaseModel):
    """Directory scan request."""
    
    path: str = Field(..., description="Directory path to scan")
    recursive: bool = Field(default=True, description="Scan subdirectories")


class ScanError(BaseModel):
    """Scan error for individual file."""
    
    path: str
    error: str


class ScanResponse(BaseModel):
    """Scan results summary."""
    
    scanned: int
    new: int
    updated: int
    skipped: int
    errors: list[ScanError]
```

## Step 2: Create Scan Service
Create `src/stoat_ferret/api/services/scan.py`:

```python
"""Directory scanning service."""

import os
from datetime import datetime, timezone
from pathlib import Path

from stoat_ferret.api.schemas.video import ScanError, ScanResponse
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.models import Video
from stoat_ferret.ffmpeg.probe import probe_video

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}


async def scan_directory(
    path: str,
    recursive: bool,
    repository: AsyncVideoRepository,
) -> ScanResponse:
    """Scan directory for video files."""
    scanned = 0
    new = 0
    updated = 0
    errors: list[ScanError] = []

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {path}")

    pattern = "**/*" if recursive else "*"
    for file_path in root.glob(pattern):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        scanned += 1
        str_path = str(file_path.absolute())

        try:
            # Check if already exists
            existing = await repository.get_by_path(str_path)
            
            # Probe video metadata
            metadata = probe_video(str_path)
            
            video = Video(
                id=existing.id if existing else Video.new_id(),
                path=str_path,
                filename=file_path.name,
                duration_frames=metadata.duration_frames,
                frame_rate_numerator=metadata.frame_rate_numerator,
                frame_rate_denominator=metadata.frame_rate_denominator,
                width=metadata.width,
                height=metadata.height,
                video_codec=metadata.video_codec,
                audio_codec=metadata.audio_codec,
                file_size=file_path.stat().st_size,
                thumbnail_path=None,
                created_at=existing.created_at if existing else datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            if existing:
                await repository.update(video)
                updated += 1
            else:
                await repository.add(video)
                new += 1

        except Exception as e:
            errors.append(ScanError(path=str_path, error=str(e)))

    skipped = scanned - new - updated - len(errors)

    return ScanResponse(
        scanned=scanned,
        new=new,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
```

## Step 3: Add Endpoint
Update `src/stoat_ferret/api/routers/videos.py`:

```python
from stoat_ferret.api.schemas.video import ScanRequest, ScanResponse
from stoat_ferret.api.services.scan import scan_directory

@router.post("/scan", response_model=ScanResponse)
async def scan_videos(
    request: ScanRequest,
    repo: AsyncVideoRepository = Depends(get_repository),
) -> ScanResponse:
    """Scan directory for video files."""
    try:
        return await scan_directory(
            path=request.path,
            recursive=request.recursive,
            repository=repo,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": str(e)},
        )
```

## Verification
- Scan finds video files
- New videos added to database
- Errors collected but don't stop scan