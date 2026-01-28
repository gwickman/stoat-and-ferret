# Clip Data Model

## Goal
Create Clip model that wraps Rust Clip for validation.

## Requirements

### FR-001: Clip Model
Create Clip dataclass:
- id: str (UUID)
- project_id: str (FK to projects)
- source_video_id: str (FK to videos)
- in_point: int (frames)
- out_point: int (frames)
- timeline_position: int (frames)
- created_at: datetime
- updated_at: datetime

### FR-002: Rust Validation
Validate clip using Rust core:
```python
from stoat_ferret_core import Clip as RustClip
RustClip.new(start, end, media_start, media_duration, frame_rate)
```

### FR-003: Database Schema
Add clips table via Alembic migration.

## Acceptance Criteria
- [ ] Clip model defined
- [ ] Validation delegates to Rust
- [ ] Invalid clips raise ClipValidationError
- [ ] Migration creates clips table