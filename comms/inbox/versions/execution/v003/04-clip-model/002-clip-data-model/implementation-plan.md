# Implementation Plan: Clip Data Model

## Step 1: Add Clip Model
Update `src/stoat_ferret/db/models.py`:

```python
from stoat_ferret_core import Clip as RustClip, ClipValidationError, FrameRate

@dataclass
class Clip:
    """Video clip within a project."""
    
    id: str
    project_id: str
    source_video_id: str
    in_point: int  # frames
    out_point: int  # frames
    timeline_position: int  # frames
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new_id(cls) -> str:
        return str(uuid.uuid4())

    def validate(self, frame_rate: FrameRate) -> None:
        """Validate clip using Rust core.
        
        Raises:
            ClipValidationError: If clip is invalid.
        """
        media_duration = self.out_point - self.in_point
        RustClip.new(
            start=self.timeline_position,
            end=self.timeline_position + media_duration,
            media_start=self.in_point,
            media_duration=media_duration,
            frame_rate=frame_rate,
        )
```

## Step 2: Create Migration
```bash
uv run alembic revision -m "add_clips_table"
```

## Step 3: Add Tests
Create `tests/test_clip_model.py` with validation tests.

## Verification
- Clip model validates via Rust
- Invalid clips raise appropriate error