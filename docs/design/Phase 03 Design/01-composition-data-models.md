# Phase 3: Composition Data Models

## Overview

Phase 3 introduces multi-clip timeline composition, transitions between clips, audio mixing across tracks, and batch processing. These data models extend the existing Clip, Project, and Effect schemas.

## Timeline Model

### Track (Python — Pydantic)

```python
class TrackType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"

class Track(BaseModel):
    id: str
    track_type: TrackType
    label: str
    z_index: int  # layer ordering, higher = on top
    muted: bool = False
    locked: bool = False
```

### TimelineClip (Python — Pydantic)

Extends existing clip model with track assignment and composition metadata.

```python
class TimelineClip(BaseModel):
    id: str
    track_id: str
    source_video_id: int
    in_point: float       # seconds into source
    out_point: float      # seconds into source
    timeline_start: float # position on timeline
    timeline_end: float   # computed: timeline_start + duration
    effects: list[dict]   # existing effect stack
    transition_in: TransitionConfig | None = None
    transition_out: TransitionConfig | None = None
```

### Timeline (Python — Pydantic)

```python
class Timeline(BaseModel):
    tracks: list[Track]
    clips: list[TimelineClip]  # clips across all tracks
    duration: float            # total timeline duration (computed)
    output_width: int
    output_height: int
    output_fps: float
```

## Transition Models

### TransitionConfig (Python — Pydantic)

```python
class TransitionConfig(BaseModel):
    transition_type: str        # "fade", "xfade", "crossfade", "cut"
    duration: float             # transition duration in seconds
    parameters: dict = {}       # type-specific params (e.g., xfade style)
    source_clip_id: str
    target_clip_id: str
```

### Rust Equivalent — TransitionSpec

```rust
#[pyclass]
pub struct TransitionSpec {
    pub transition_type: TransitionType,  // existing enum (46 types)
    pub duration: f64,
    pub offset: f64,  // computed overlap offset
}
```

The existing `FadeBuilder`, `XfadeBuilder`, and `AcrossfadeBuilder` from Phase 2 handle filter generation. Phase 3 adds timeline-aware offset calculation.

## Audio Mixing Models

### AudioTrackConfig (Python — Pydantic)

```python
class AudioTrackConfig(BaseModel):
    track_id: str
    volume: float = 1.0        # 0.0 to 2.0
    fade_in: float = 0.0       # seconds
    fade_out: float = 0.0      # seconds
    muted: bool = False
```

### AudioMixConfig (Python — Pydantic)

```python
class AudioMixConfig(BaseModel):
    tracks: list[AudioTrackConfig]
    master_volume: float = 1.0
    normalize: bool = False
```

### Rust Equivalent — AudioMixSpec

```rust
#[pyclass]
pub struct AudioMixSpec {
    pub track_volumes: Vec<f64>,
    pub fade_ins: Vec<f64>,
    pub fade_outs: Vec<f64>,
    pub master_volume: f64,
    pub normalize: bool,
}
```

The existing `AmixBuilder`, `VolumeBuilder`, and `AfadeBuilder` from Phase 2 handle filter generation. Phase 3 adds multi-track coordination.

## Layout Models (PIP / Split-Screen)

### LayoutPosition (Python — Pydantic)

```python
class LayoutPosition(BaseModel):
    x: float        # 0.0-1.0 normalized position
    y: float        # 0.0-1.0 normalized position
    width: float    # 0.0-1.0 normalized size
    height: float   # 0.0-1.0 normalized size
    z_index: int = 0
```

### LayoutPreset (Python — Pydantic)

```python
class LayoutPreset(str, Enum):
    PIP_TOP_LEFT = "pip_top_left"
    PIP_TOP_RIGHT = "pip_top_right"
    PIP_BOTTOM_LEFT = "pip_bottom_left"
    PIP_BOTTOM_RIGHT = "pip_bottom_right"
    SIDE_BY_SIDE = "side_by_side"
    TOP_BOTTOM = "top_bottom"
    GRID_2X2 = "grid_2x2"
```

### Rust Equivalent — LayoutSpec

```rust
#[pyclass]
pub struct LayoutSpec {
    pub positions: Vec<LayoutPosition>,
    pub output_width: u32,
    pub output_height: u32,
    pub background_color: String,
}

#[pyclass]
#[derive(Clone)]
pub struct LayoutPosition {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
    pub z_index: i32,
}
```

## Batch Processing Models

### BatchJob (Python — Pydantic)

```python
class BatchJobRequest(BaseModel):
    project_id: str
    output_path: str
    quality: str = "high"     # "draft", "medium", "high"

class BatchRequest(BaseModel):
    jobs: list[BatchJobRequest]
    parallel: int = 1         # max concurrent renders

class BatchStatus(BaseModel):
    batch_id: str
    total: int
    completed: int
    failed: int
    in_progress: int
    jobs: list[JobStatusResponse]
```

## Project Persistence (Extended)

### ProjectVersion (Python — Pydantic)

```python
class ProjectVersion(BaseModel):
    version: int
    timestamp: str           # ISO 8601
    timeline: Timeline
    checksum: str            # integrity verification
```

Existing `Project` dataclass in `db/models.py` extends with:
- `timeline_json: str | None` — serialized Timeline
- `version: int` — auto-incrementing version number

## Database Schema Additions

```sql
-- Track table
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    track_type TEXT NOT NULL,
    label TEXT NOT NULL,
    z_index INTEGER NOT NULL DEFAULT 0,
    muted INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0
);

-- Extend clips table with track_id and timeline positioning
ALTER TABLE clips ADD COLUMN track_id TEXT REFERENCES tracks(id);
ALTER TABLE clips ADD COLUMN timeline_start REAL;
ALTER TABLE clips ADD COLUMN timeline_end REAL;

-- Project versions for undo/recovery
CREATE TABLE IF NOT EXISTS project_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    version INTEGER NOT NULL,
    timeline_json TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, version)
);
```

## Relationship to Existing Models

| Existing Model | Phase 3 Extension |
|---------------|-------------------|
| `Clip` (db/models.py) | Add `track_id`, `timeline_start`, `timeline_end` |
| `Project` (db/models.py) | Add `timeline_json`, `version` |
| `ClipCreate` (schemas/clip.py) | Add `track_id` field |
| `ClipResponse` (schemas/clip.py) | Add `timeline_start`, `timeline_end`, `track_id` |
| `ProjectResponse` (schemas/project.py) | Add `tracks`, `timeline_duration`, `version` |
| `TransitionRequest` (schemas/effect.py) | Already exists; add timeline offset computation |
