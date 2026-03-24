# Phase 5: Export Data Models

## Overview

Phase 5 introduces render job management, output format configuration, hardware encoder detection, and render checkpoint recovery. These data models extend the existing Job, Project, and Settings schemas established in Phases 1-3, and integrate with the WebSocket push pattern established in Phase 4 (BL-141).

## Render Job Model

### RenderJob (Python - Pydantic)

```python
class RenderStatus(str, Enum):
    PENDING = "pending"           # queued, waiting for resources
    PREPARING = "preparing"       # validating timeline, building render plan
    RENDERING = "rendering"       # FFmpeg process active (single-pass or pass 2)
    ENCODING_PASS_1 = "pass_1"   # two-pass: analysis pass
    ENCODING_PASS_2 = "pass_2"   # two-pass: encoding pass
    FINALIZING = "finalizing"     # muxing, moving to output path
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OutputFormat(str, Enum):
    MP4 = "mp4"         # H.264/H.265 in MP4 container (default)
    WEBM = "webm"       # VP9 in WebM container
    PRORES = "prores"   # Apple ProRes in MOV container (editing interchange)
    MOV = "mov"         # H.264/H.265 in MOV container

class QualityPreset(str, Enum):
    DRAFT = "draft"         # fast encode, lower quality (preview/test renders)
    MEDIUM = "medium"       # balanced speed/quality
    HIGH = "high"           # high quality, slower encode (default)
    LOSSLESS = "lossless"   # lossless or near-lossless (archival)

class RenderJob(BaseModel):
    id: str                         # render job UUID
    project_id: str
    status: RenderStatus
    output_format: OutputFormat
    quality_preset: QualityPreset

    # Output
    output_path: str                # final output file path
    output_dir: str                 # directory for render artifacts
    file_size_bytes: int | None     # populated on completion

    # Progress
    progress: float                 # 0.0 to 1.0
    current_frame: int              # frames rendered so far
    total_frames: int               # estimated total frames
    eta_seconds: float | None       # estimated time remaining
    elapsed_seconds: float          # time since render started
    fps: float                      # current render speed (frames/sec)

    # Encoding
    encoder: str                    # selected encoder (e.g., "libx264", "h264_nvenc")
    hardware_accelerated: bool      # whether HW encoder is in use
    two_pass: bool                  # whether two-pass encoding is active
    pass_number: int | None         # 1 or 2 if two_pass, else None

    # Resolution and codec
    output_width: int
    output_height: int
    output_fps: float
    video_bitrate: int | None       # bps, None for CRF/CQ mode
    audio_bitrate: int              # bps

    # Lifecycle
    created_at: str                 # ISO 8601
    started_at: str | None
    completed_at: str | None
    failed_at: str | None

    # Error handling
    error_message: str | None
    error_code: str | None
    retry_count: int                # number of retries attempted
    max_retries: int                # configured max retries

    # FFmpeg command (for debugging/transparency)
    ffmpeg_command: str | None      # full command string
```

### Render Status State Machine

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ start_render (resources available)
                    ┌────▼──────┐
                    │ PREPARING │
                    └────┬──────┘
                         │ render_plan_built
                    ┌────▼──────┐
            ┌───────┤ RENDERING │◄────────────┐
            │       └────┬──────┘             │
            │            │                    │
            │   (two_pass│only)               │
            │   ┌────────▼────────┐           │
            │   │ ENCODING_PASS_1 │           │
            │   └────────┬────────┘           │
            │            │ pass_1_complete     │
            │   ┌────────▼────────┐           │
            │   │ ENCODING_PASS_2 │           │
            │   └────────┬────────┘           │
            │            │                    │
            │            ├────────────────────┘
            │            │ encoding_complete
            │   ┌────────▼─────┐
            │   │  FINALIZING  │
            │   └────────┬─────┘
            │            │ finalize_complete
            │   ┌────────▼──────┐
            │   │   COMPLETED   │
            │   └───────────────┘
            │
    cancel  │            error (at any active state)
    ┌───────▼──────┐     ┌────────┐
    │  CANCELLED   │     │ FAILED │ → retry? → PENDING
    └──────────────┘     └────────┘
```

## Render Plan Model

### RenderPlan (Rust struct, exposed via PyO3)

```python
class RenderSegment(BaseModel):
    """A segment of the timeline to render independently."""
    index: int
    start_time: float       # timeline start (seconds)
    end_time: float         # timeline end (seconds)
    filter_graph: str       # FFmpeg filter graph string
    input_files: list[str]  # source video paths needed

class RenderPlan(BaseModel):
    """Complete plan for rendering a timeline to output."""
    segments: list[RenderSegment]
    total_frames: int
    total_duration: float
    estimated_cost: float       # relative computational cost (0.0-1.0)
    requires_concat: bool       # whether segments need final concatenation
    audio_mix_graph: str | None # audio mixing filter graph
```

## Hardware Encoder Model

### HardwareEncoder (Rust struct, exposed via PyO3)

```python
class EncoderType(str, Enum):
    NVENC = "nvenc"             # NVIDIA GPU
    VAAPI = "vaapi"            # Intel/AMD on Linux
    VIDEOTOOLBOX = "videotoolbox"  # macOS
    QSV = "qsv"               # Intel Quick Sync
    SOFTWARE = "software"       # CPU fallback (always available)

class HardwareEncoder(BaseModel):
    name: str                   # FFmpeg encoder name (e.g., "h264_nvenc")
    encoder_type: EncoderType
    available: bool             # detected as usable
    priority: int               # selection order (lower = preferred)
    supported_formats: list[OutputFormat]  # which output formats this encoder supports
    max_resolution: tuple[int, int] | None  # hardware limit, if known
```

### Encoder Fallback Chain

```python
def select_encoder(
    format: OutputFormat,
    hw_encoders: list[HardwareEncoder],
) -> HardwareEncoder:
    """Select best available encoder for the output format.

    Fallback chain: HW encoder (by priority) -> SW encoder -> error.
    Pure function implemented in Rust, exposed via PyO3.
    """
    ...
```

Default fallback chains by format:

| Format | Preferred | Fallback 1 | Fallback 2 | SW Fallback |
|--------|-----------|------------|------------|-------------|
| MP4 (H.264) | h264_nvenc | h264_vaapi | h264_videotoolbox | libx264 |
| MP4 (H.265) | hevc_nvenc | hevc_vaapi | hevc_videotoolbox | libx265 |
| WebM (VP9) | — (no HW) | — | — | libvpx-vp9 |
| ProRes | prores_videotoolbox | — | — | prores_ks |
| MOV (H.264) | Same as MP4 H.264 chain | | | |

## Render Checkpoint Model

### RenderCheckpoint (Python - for crash recovery)

```python
class RenderCheckpoint(BaseModel):
    job_id: str
    segment_index: int          # last completed segment
    completed_segments: int     # total segments completed
    total_segments: int
    output_temp_dir: str        # where partial render files live
    checkpoint_time: str        # ISO 8601
    ffmpeg_log_path: str | None # path to FFmpeg stderr log
```

Checkpoints are written to SQLite after each segment completes. On server restart, the render service queries unfinished jobs and resumes from the last checkpoint.

## Render Queue Model

### RenderQueue (Python - internal)

```python
class RenderQueueConfig(BaseModel):
    max_concurrent_renders: int = 2         # simultaneous render jobs
    max_queue_depth: int = 20               # pending jobs before rejection
    render_timeout_seconds: int = 7200      # 2 hours per job max
    retry_max_attempts: int = 2             # retries for transient failures
    retry_delay_seconds: int = 30           # delay between retries
    cleanup_completed_after_hours: int = 24 # remove completed job metadata
```

## Database Schema Additions

```sql
-- Render jobs table
CREATE TABLE IF NOT EXISTS render_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    status TEXT NOT NULL DEFAULT 'pending',
    output_format TEXT NOT NULL DEFAULT 'mp4',
    quality_preset TEXT NOT NULL DEFAULT 'high',
    output_path TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    file_size_bytes INTEGER,
    progress REAL NOT NULL DEFAULT 0.0,
    current_frame INTEGER NOT NULL DEFAULT 0,
    total_frames INTEGER NOT NULL DEFAULT 0,
    eta_seconds REAL,
    elapsed_seconds REAL NOT NULL DEFAULT 0.0,
    fps REAL NOT NULL DEFAULT 0.0,
    encoder TEXT,
    hardware_accelerated INTEGER NOT NULL DEFAULT 0,
    two_pass INTEGER NOT NULL DEFAULT 0,
    pass_number INTEGER,
    output_width INTEGER NOT NULL,
    output_height INTEGER NOT NULL,
    output_fps REAL NOT NULL,
    video_bitrate INTEGER,
    audio_bitrate INTEGER NOT NULL DEFAULT 192000,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    failed_at TEXT,
    error_message TEXT,
    error_code TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2,
    ffmpeg_command TEXT
);

-- Render checkpoints table (for crash recovery)
CREATE TABLE IF NOT EXISTS render_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    completed_segments INTEGER NOT NULL,
    total_segments INTEGER NOT NULL,
    output_temp_dir TEXT NOT NULL,
    checkpoint_time TEXT NOT NULL DEFAULT (datetime('now')),
    ffmpeg_log_path TEXT,
    UNIQUE(job_id, segment_index)
);

-- Hardware encoder cache (detected once, reused)
CREATE TABLE IF NOT EXISTS hardware_encoders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    encoder_type TEXT NOT NULL,
    available INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 100,
    detected_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index for active render queries
CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status);
CREATE INDEX IF NOT EXISTS idx_render_jobs_project ON render_jobs(project_id);
```

## Relationship to Existing Models

| Existing Model | Phase 5 Extension |
|---------------|-------------------|
| `Project` (db/models.py) | Add `last_render_job_id` for quick access to most recent render |
| `JobType` (jobs/queue.py) | Add `RENDER`, `RENDER_SEGMENT` job types |
| `Settings` (config.py) | Add render queue, output, and hardware acceleration settings |
| `BatchRenderState` (BL-143) | Render jobs extend the persisted batch state pattern |

## Configuration Extensions

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Render settings
    render_output_dir: str = "data/renders"
    render_temp_dir: str = "data/renders/temp"
    render_max_concurrent: int = 2          # (ge=1, le=8)
    render_max_queue_depth: int = 20        # (ge=1, le=100)
    render_timeout_seconds: int = 7200      # (ge=300, le=86400)
    render_retry_max_attempts: int = 2      # (ge=0, le=5)
    render_retry_delay_seconds: int = 30    # (ge=5, le=300)
    render_cleanup_hours: int = 24          # (ge=1, le=720)

    # Output defaults
    render_default_format: str = "mp4"
    render_default_quality: str = "high"
    render_default_width: int = 1920        # (ge=320, le=7680)
    render_default_height: int = 1080       # (ge=240, le=4320)
    render_default_fps: float = 30.0        # (ge=1.0, le=120.0)
    render_default_video_bitrate: int = 8_000_000   # bps
    render_default_audio_bitrate: int = 192_000      # bps
    render_two_pass_default: bool = True   # default on for "high" quality

    # Hardware acceleration
    render_hw_accel_enabled: bool = True     # attempt HW detection
    render_hw_accel_prefer: str | None = None  # force specific encoder type

    # Parallel rendering (future: Phase 5 renders sequentially, threshold for future activation)
    render_parallel_min_duration_seconds: int = 300  # 5 min; parallel only for timelines >= this
    render_segment_duration_seconds: int = 30        # segment length when parallel rendering active

    # Disk space safety
    render_min_free_disk_bytes: int = 1_073_741_824  # 1 GB minimum free (ge=104_857_600)
```

## Quality Preset Definitions

| Preset | Video Codec | CRF/CQ | Preset | Audio | Two-Pass |
|--------|-------------|---------|--------|-------|----------|
| Draft | libx264 | 28 | ultrafast | 128k AAC | No |
| Medium | libx264 | 23 | medium | 192k AAC | No |
| High | libx264 | 18 | slow | 320k AAC | Yes (default) |
| Lossless | libx264 | 0 | veryslow | FLAC | No |

For H.265 (MP4 with HEVC):

| Preset | CRF | Preset |
|--------|-----|--------|
| Draft | 32 | ultrafast |
| Medium | 28 | medium |
| High | 22 | slow |
| Lossless | 0 | veryslow |

For VP9 (WebM):

| Preset | CQ | Speed |
|--------|-----|-------|
| Draft | 40 | 4 |
| Medium | 33 | 2 |
| High | 25 | 1 |
| Lossless | 0 | 0 |

For ProRes:

| Preset | Profile |
|--------|---------|
| Draft | proxy (0) |
| Medium | lt (1) |
| High | standard (2) |
| Lossless | hq (3) |
