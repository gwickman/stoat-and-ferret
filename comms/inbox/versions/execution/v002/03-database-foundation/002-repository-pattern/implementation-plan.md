# Implementation Plan: Repository Pattern

## Step 1: Create Video Dataclass
In `src/stoat_ferret/db/models.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class Video:
    id: str
    path: str
    filename: str
    duration_frames: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    width: int
    height: int
    video_codec: str
    file_size: int
    created_at: datetime
    updated_at: datetime
    audio_codec: Optional[str] = None
    thumbnail_path: Optional[str] = None
    
    @property
    def frame_rate(self) -> float:
        return self.frame_rate_numerator / self.frame_rate_denominator
    
    @property
    def duration_seconds(self) -> float:
        return self.duration_frames / self.frame_rate
    
    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
```

## Step 2: Define Protocol
In `src/stoat_ferret/db/repository.py`:

```python
from typing import Protocol
from .models import Video

class VideoRepository(Protocol):
    def add(self, video: Video) -> Video: ...
    def get(self, id: str) -> Video | None: ...
    def get_by_path(self, path: str) -> Video | None: ...
    def list(self, limit: int = 100, offset: int = 0) -> list[Video]: ...
    def search(self, query: str, limit: int = 100) -> list[Video]: ...
    def update(self, video: Video) -> Video: ...
    def delete(self, id: str) -> bool: ...
```

## Step 3: Implement SQLiteVideoRepository
```python
import sqlite3
from datetime import datetime

class SQLiteVideoRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
    
    def add(self, video: Video) -> Video:
        self._conn.execute("""
            INSERT INTO videos (id, path, filename, duration_frames, 
                frame_rate_numerator, frame_rate_denominator, width, height,
                video_codec, audio_codec, file_size, thumbnail_path, 
                created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (video.id, video.path, video.filename, video.duration_frames,
              video.frame_rate_numerator, video.frame_rate_denominator,
              video.width, video.height, video.video_codec, video.audio_codec,
              video.file_size, video.thumbnail_path,
              video.created_at.isoformat(), video.updated_at.isoformat()))
        self._conn.commit()
        return video
    
    def get(self, id: str) -> Video | None:
        cursor = self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
        row = cursor.fetchone()
        return self._row_to_video(row) if row else None
    
    # ... other methods following same pattern
    
    def _row_to_video(self, row: sqlite3.Row) -> Video:
        return Video(
            id=row["id"],
            path=row["path"],
            # ... all fields
        )
```

## Step 4: Implement InMemoryVideoRepository
```python
class InMemoryVideoRepository:
    def __init__(self):
        self._videos: dict[str, Video] = {}
        self._by_path: dict[str, str] = {}  # path -> id for fast lookup
    
    def add(self, video: Video) -> Video:
        if video.id in self._videos:
            raise ValueError(f"Video {video.id} already exists")
        if video.path in self._by_path:
            raise ValueError(f"Video with path {video.path} already exists")
        self._videos[video.id] = video
        self._by_path[video.path] = video.id
        return video
    
    def search(self, query: str, limit: int = 100) -> list[Video]:
        query_lower = query.lower()
        results = [
            v for v in self._videos.values()
            if query_lower in v.filename.lower() or query_lower in v.path.lower()
        ]
        return results[:limit]
    
    # ... other methods implementing same logic
```

## Step 5: Create Contract Tests
In `tests/test_repository_contract.py`:

```python
import pytest
import sqlite3
from datetime import datetime
from stoat_ferret.db.schema import create_tables
from stoat_ferret.db.repository import SQLiteVideoRepository, InMemoryVideoRepository
from stoat_ferret.db.models import Video

def make_test_video(**kwargs) -> Video:
    defaults = {
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
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return Video(**defaults)

@pytest.fixture(params=["sqlite", "memory"])
def repository(request):
    if request.param == "sqlite":
        conn = sqlite3.connect(":memory:")
        create_tables(conn)
        return SQLiteVideoRepository(conn)
    else:
        return InMemoryVideoRepository()

def test_add_and_get(repository):
    video = make_test_video()
    repository.add(video)
    retrieved = repository.get(video.id)
    assert retrieved is not None
    assert retrieved.path == video.path

def test_get_nonexistent(repository):
    assert repository.get("nonexistent") is None

def test_search(repository):
    video = make_test_video(filename="my_cool_video.mp4")
    repository.add(video)
    results = repository.search("cool")
    assert len(results) == 1
    assert results[0].id == video.id

def test_delete(repository):
    video = make_test_video()
    repository.add(video)
    assert repository.delete(video.id)
    assert repository.get(video.id) is None
```

## Verification
- Contract tests pass for both implementations
- `uv run pytest tests/test_repository_contract.py -v`