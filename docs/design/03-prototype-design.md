# stoat-and-ferret - Prototype Design (MVP)

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Prototype Scope

This document defines the Minimum Viable Product (MVP) for the AI-driven video editor using a **hybrid Python/Rust architecture**. Python provides the API layer for AI discoverability and rapid iteration, while Rust delivers high-performance compute cores for video processing operations.

**Goal:** A working system that can scan a video library, create a simple montage with effects, and render the output - all via API, with compute-intensive operations running in Rust.

**Quality Goal:** The MVP includes production-ready quality infrastructure from day one. Testing, observability, and operability are not deferred - they are part of the foundation.

**Performance Goal:** Establish the hybrid architecture pattern from MVP, with Rust handling timeline math, filter generation, and input sanitization.

---

## MVP Feature Set

### In Scope (Must Have)

| Feature | Description | Implementation |
|---------|-------------|----------------|
| Library Scan | Scan directory (async job), extract metadata, generate thumbnails | Python + asyncio.Queue job queue |
| Video Search | Full-text search across filenames and metadata | Python (SQLite FTS5) |
| Basic Timeline | Single video track with clips | Python API + Rust timeline math |
| Text Overlay | Add text with position and basic fade | Rust filter builder |
| Speed Control | Constant speed change (0.5x to 4x) | Rust filter builder |
| Simple Concat | Join clips sequentially | Rust command builder |
| Export | Render timeline to MP4 | Python orchestration + Rust command |
| REST API | All operations available via HTTP | Python (FastAPI) |

### Quality Infrastructure (Must Have)

| Feature | Description | Implementation |
|---------|-------------|----------------|
| Structured Logging | JSON logs with correlation IDs | Python (structlog) |
| Metrics Endpoint | Prometheus-compatible /metrics | Python (prometheus-client) |
| Health Checks | /health/live, /health/ready (includes Rust check) | Python |
| Externalized Config | Environment variable configuration | Python (pydantic-settings) |
| Graceful Shutdown | Complete in-flight work before exit | Python |
| Test Suite | >80% Python coverage, >90% Rust coverage | pytest + cargo test |
| Structured Errors | Helpful error responses with suggestions | Python + Rust error types |

### GUI (Must Have)

| Feature | Description | Implementation |
|---------|-------------|----------------|
| Operations Dashboard | Health status, metrics, activity log | React/Svelte + WebSocket |
| Library Browser | Video grid with search and thumbnails | REST API integration |
| Project Manager | Create/open projects, view clips | REST API integration |
| Real-time Updates | Live activity feed and status | WebSocket events |

### Out of Scope (Future Phases)

- Multi-track composition (PIP, split-screen)
- Real-time preview with libmpv
- Hardware-accelerated encoding
- Audio mixing (beyond pass-through)
- Complex transitions (xfade)
- Proxy workflow
- AI Theater Mode (Phase 4)
- Effect Workshop (Phase 2)
- Visual Timeline (Phase 3)
- Distributed tracing (optional in MVP)

---

## Prototype Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Web GUI (React/Svelte)                           │
│  Dashboard  │  Library Browser  │  Project Manager                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Components: Health Status │ Video Grid │ Project List          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ REST + WebSocket
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                         REST API (FastAPI)                               │
│  /videos  /jobs  /projects  /clips  /effects  /render  /health /metrics │
│  /ws (WebSocket)  /gui/* (static files)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Middleware: Correlation ID → Metrics → Error Handler           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                    Python Service Layer (Injectable)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   Library   │ │   Timeline  │ │   Render    │ │   Audit     │       │
│  │   Service   │ │   Service   │ │   Service   │ │   Service   │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                             PyO3 Bindings
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                    Rust Core Library (Performance)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │  Timeline   │ │   Filter    │ │   Command   │ │   Input     │       │
│  │    Math     │ │   Builder   │ │   Builder   │ │  Sanitizer  │       │
│  │ (pure fn)   │ │  (pure fn)  │ │  (pure fn)  │ │ (security)  │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                    Python Processing Layer                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                       │
│  │   FFprobe   │ │   FFmpeg    │ │    Job      │                       │
│  │   Wrapper   │ │  Executor   │ │   Queue     │                       │
│  │             │ │ (Protocol)  │ │             │                       │
│  └─────────────┘ └─────────────┘ └─────────────┘                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                    Storage (Repository Pattern)                          │
│        SQLite (metadata + audit)    +    JSON (projects + versions)     │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────┐
│                    Observability (Cross-Cutting)                         │
│        Structured Logs (JSON)    │    Metrics (/metrics)                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Quality Patterns in MVP

| Pattern | Implementation | Benefit |
|---------|---------------|---------|
| Dependency Injection | Services receive dependencies via constructor | Testability |
| Pure Functions (Rust) | Filter/timeline builders have no side effects | Testability, Performance |
| Protocol Interfaces | Python protocols for services | Testability |
| Repository Pattern | Storage behind interfaces | Testability |
| Correlation IDs | Every request gets unique ID | Debuggability |
| Structured Logging | JSON with context | Observability |
| Health Checks | /health/live, /health/ready (+ Rust check) | Operability |
| Externalized Config | Environment variables | Operability |
| Graceful Shutdown | Complete in-flight work | Reliability |
| Rust Sanitization | Compile-time security guarantees | Security |

---

## Rust Core Library (MVP)

The Rust core library provides high-performance, tested pure functions for compute-intensive operations.

### Module Structure

```rust
// stoat_ferret_core/src/lib.rs
pub mod timeline;     // Timeline math and validation
pub mod filters;      // FFmpeg filter builders
pub mod commands;     // FFmpeg command construction
pub mod sanitize;     // Input validation and escaping

use pyo3::prelude::*;

#[pymodule]
fn stoat_ferret_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Timeline functions
    m.add_function(wrap_pyfunction!(py_calculate_clip_positions, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_time_range, m)?)?;

    // Filter builders
    m.add_function(wrap_pyfunction!(py_build_text_overlay_filter, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_speed_filters, m)?)?;

    // Command builders
    m.add_function(wrap_pyfunction!(py_build_concat_command, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_render_command, m)?)?;

    // Sanitization
    m.add_function(wrap_pyfunction!(py_validate_path, m)?)?;
    m.add_function(wrap_pyfunction!(py_escape_ffmpeg_text, m)?)?;

    // Version info
    m.add_function(wrap_pyfunction!(version, m)?)?;

    Ok(())
}

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
```

### Timeline Module

```rust
// stoat_ferret_core/src/timeline.rs
use pyo3::prelude::*;

#[derive(Clone, Debug)]
#[pyclass]
pub struct ClipInput {
    #[pyo3(get, set)]
    pub source: String,
    #[pyo3(get, set)]
    pub in_point: f64,
    #[pyo3(get, set)]
    pub out_point: f64,
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct ClipWithPosition {
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub in_point: f64,
    #[pyo3(get)]
    pub out_point: f64,
    #[pyo3(get)]
    pub timeline_start: f64,
    #[pyo3(get)]
    pub timeline_end: f64,
    #[pyo3(get)]
    pub duration: f64,
}

/// Calculate timeline positions for sequential clips.
/// Pure function - deterministic, no side effects.
pub fn calculate_clip_positions(clips: &[ClipInput]) -> Vec<ClipWithPosition> {
    let mut result = Vec::with_capacity(clips.len());
    let mut current_position = 0.0;

    for clip in clips {
        let duration = clip.out_point - clip.in_point;
        result.push(ClipWithPosition {
            source: clip.source.clone(),
            in_point: clip.in_point,
            out_point: clip.out_point,
            timeline_start: current_position,
            timeline_end: current_position + duration,
            duration,
        });
        current_position += duration;
    }

    result
}

#[pyfunction]
pub fn py_calculate_clip_positions(clips: Vec<ClipInput>) -> Vec<ClipWithPosition> {
    calculate_clip_positions(&clips)
}

/// Validate time range with detailed error.
#[derive(Debug, Clone)]
pub enum TimeRangeError {
    NegativeInPoint { value: f64 },
    OutBeforeIn { in_point: f64, out_point: f64 },
    OutBeyondDuration { out_point: f64, duration: f64 },
}

impl std::fmt::Display for TimeRangeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NegativeInPoint { value } =>
                write!(f, "in_point cannot be negative: {}", value),
            Self::OutBeforeIn { in_point, out_point } =>
                write!(f, "out_point ({}) must be greater than in_point ({})", out_point, in_point),
            Self::OutBeyondDuration { out_point, duration } =>
                write!(f, "out_point ({}) exceeds source duration ({})", out_point, duration),
        }
    }
}

pub fn validate_time_range(
    in_point: f64,
    out_point: f64,
    source_duration: f64,
) -> Result<(), TimeRangeError> {
    if in_point < 0.0 {
        return Err(TimeRangeError::NegativeInPoint { value: in_point });
    }
    if out_point <= in_point {
        return Err(TimeRangeError::OutBeforeIn { in_point, out_point });
    }
    if out_point > source_duration {
        return Err(TimeRangeError::OutBeyondDuration { out_point, duration: source_duration });
    }
    Ok(())
}
```

### Filter Builders Module

```rust
// stoat_ferret_core/src/filters.rs
use crate::sanitize::escape_ffmpeg_text;

#[derive(Clone, Debug)]
pub struct TextOverlayParams {
    pub text: String,
    pub position: TextPosition,
    pub font_size: u32,
    pub font_color: String,
    pub start: f64,
    pub duration: f64,
    pub fade_in: f64,
    pub fade_out: f64,
}

#[derive(Clone, Debug)]
pub enum TextPosition {
    Center,
    Top,
    Bottom,
    TopLeft,
    TopRight,
    BottomLeft,
    BottomRight,
}

impl TextPosition {
    pub fn to_coordinates(&self) -> (String, String) {
        match self {
            Self::Center => ("(w-text_w)/2".to_string(), "(h-text_h)/2".to_string()),
            Self::Top => ("(w-text_w)/2".to_string(), "50".to_string()),
            Self::Bottom => ("(w-text_w)/2".to_string(), "h-text_h-50".to_string()),
            Self::TopLeft => ("50".to_string(), "50".to_string()),
            Self::TopRight => ("w-text_w-50".to_string(), "50".to_string()),
            Self::BottomLeft => ("50".to_string(), "h-text_h-50".to_string()),
            Self::BottomRight => ("w-text_w-50".to_string(), "h-text_h-50".to_string()),
        }
    }
}

/// Build FFmpeg drawtext filter.
/// Pure function - same inputs always produce same outputs.
/// Text is automatically sanitized.
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> String {
    let sanitized_text = escape_ffmpeg_text(&params.text);
    let (x, y) = params.position.to_coordinates();
    let end_time = params.start + params.duration;

    let mut filter = format!(
        "drawtext=text='{}':fontsize={}:fontcolor={}:x={}:y={}",
        sanitized_text, params.font_size, params.font_color, x, y
    );

    // Enable expression for timing
    filter.push_str(&format!(":enable='between(t,{},{})'", params.start, end_time));

    // Alpha expression for fades
    if params.fade_in > 0.0 || params.fade_out > 0.0 {
        let alpha_expr = build_alpha_expression(
            params.start,
            end_time,
            params.fade_in,
            params.fade_out,
        );
        filter.push_str(&format!(":alpha='{}'", alpha_expr));
    }

    filter
}

fn build_alpha_expression(start: f64, end: f64, fade_in: f64, fade_out: f64) -> String {
    let fade_in_end = start + fade_in;
    let fade_out_start = end - fade_out;
    let fade_in_safe = fade_in.max(0.001);
    let fade_out_safe = fade_out.max(0.001);

    format!(
        "if(lt(t,{}),(t-{})/{},if(gt(t,{}),({}-t)/{},1))",
        fade_in_end, start, fade_in_safe,
        fade_out_start, end, fade_out_safe
    )
}

/// Build FFmpeg filters for speed change.
#[derive(Clone, Debug)]
pub struct SpeedFilters {
    pub video: String,
    pub audio: Option<String>,
}

pub fn build_speed_filters(speed: f64, include_audio: bool) -> SpeedFilters {
    // Video: PTS manipulation
    let video_filter = format!("setpts={:.4}*PTS", 1.0 / speed);

    // Audio: atempo chain (atempo limited to 0.5-2.0)
    let audio_filter = if include_audio && (0.25..=4.0).contains(&speed) {
        Some(build_atempo_chain(speed))
    } else {
        None
    };

    SpeedFilters {
        video: video_filter,
        audio: audio_filter,
    }
}

fn build_atempo_chain(speed: f64) -> String {
    let mut remaining = speed;
    let mut filters = Vec::new();

    while remaining > 2.0 {
        filters.push("atempo=2.0".to_string());
        remaining /= 2.0;
    }
    while remaining < 0.5 {
        filters.push("atempo=0.5".to_string());
        remaining /= 0.5;
    }
    filters.push(format!("atempo={:.4}", remaining));

    filters.join(",")
}
```

### Sanitization Module

```rust
// stoat_ferret_core/src/sanitize.rs
use std::path::{Path, PathBuf};

/// Escape text for FFmpeg drawtext filter.
/// Prevents command injection through filter parameters.
pub fn escape_ffmpeg_text(text: &str) -> String {
    text.chars()
        .map(|c| match c {
            '\\' => "\\\\".to_string(),
            '\'' => "'\\''".to_string(),
            ':' => "\\:".to_string(),
            '%' => "%%".to_string(),
            _ => c.to_string(),
        })
        .collect()
}

#[derive(Debug, Clone)]
pub enum PathValidationError {
    CannotResolve { path: PathBuf, reason: String },
    OutsideAllowedRoots { path: PathBuf, allowed: Vec<PathBuf> },
}

impl std::fmt::Display for PathValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::CannotResolve { path, reason } =>
                write!(f, "Cannot resolve path {:?}: {}", path, reason),
            Self::OutsideAllowedRoots { path, allowed } =>
                write!(f, "Path {:?} is outside allowed directories: {:?}", path, allowed),
        }
    }
}

/// Validate path is within allowed directories.
/// MUST be called before any filesystem operation with user input.
pub fn validate_path(
    user_path: &Path,
    allowed_roots: &[PathBuf],
) -> Result<PathBuf, PathValidationError> {
    let resolved = user_path.canonicalize()
        .map_err(|e| PathValidationError::CannotResolve {
            path: user_path.to_path_buf(),
            reason: e.to_string(),
        })?;

    for root in allowed_roots {
        if let Ok(canonical_root) = root.canonicalize() {
            if resolved.starts_with(&canonical_root) {
                return Ok(resolved);
            }
        }
    }

    Err(PathValidationError::OutsideAllowedRoots {
        path: user_path.to_path_buf(),
        allowed: allowed_roots.to_vec(),
    })
}
```

### Rust Tests (MVP)

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Property-based tests with proptest
    proptest! {
        #[test]
        fn text_sanitizer_escapes_all_dangerous_chars(text in ".*") {
            let escaped = escape_ffmpeg_text(&text);
            // Verify no unescaped single quotes
            assert!(!escaped.contains("'") ||
                    escaped.contains("'\\''") ||
                    !text.contains("'"));
        }

        #[test]
        fn filter_builder_never_panics(
            text in ".*",
            font_size in 8u32..500,
            start in 0.0f64..1000.0,
            duration in 0.1f64..100.0,
        ) {
            let params = TextOverlayParams {
                text,
                position: TextPosition::Center,
                font_size,
                font_color: "white".to_string(),
                start,
                duration,
                fade_in: 0.0,
                fade_out: 0.0,
            };
            // Should never panic
            let _ = build_text_overlay_filter(&params);
        }

        #[test]
        fn speed_filter_valid_for_any_speed(speed in 0.1f64..10.0) {
            let filters = build_speed_filters(speed, true);
            assert!(!filters.video.is_empty());
            assert!(filters.video.contains("setpts="));
        }
    }

    #[test]
    fn timeline_positions_calculated_correctly() {
        let clips = vec![
            ClipInput {
                source: "a.mp4".to_string(),
                in_point: 0.0,
                out_point: 10.0,
            },
            ClipInput {
                source: "b.mp4".to_string(),
                in_point: 5.0,
                out_point: 15.0,
            },
        ];

        let result = calculate_clip_positions(&clips);

        assert_eq!(result.len(), 2);
        assert_eq!(result[0].timeline_start, 0.0);
        assert_eq!(result[0].timeline_end, 10.0);
        assert_eq!(result[1].timeline_start, 10.0);
        assert_eq!(result[1].timeline_end, 20.0);
    }

    #[test]
    fn time_range_validation() {
        // Valid range
        assert!(validate_time_range(0.0, 10.0, 30.0).is_ok());

        // Negative in_point
        assert!(matches!(
            validate_time_range(-1.0, 10.0, 30.0),
            Err(TimeRangeError::NegativeInPoint { .. })
        ));

        // out <= in
        assert!(matches!(
            validate_time_range(10.0, 5.0, 30.0),
            Err(TimeRangeError::OutBeforeIn { .. })
        ));

        // out > duration
        assert!(matches!(
            validate_time_range(0.0, 40.0, 30.0),
            Err(TimeRangeError::OutBeyondDuration { .. })
        ));
    }
}
```

---

## API Specification (MVP)

### Library Endpoints

#### Scan Directory (Async)
```http
POST /videos/scan
Content-Type: application/json

{
  "path": "/home/user/videos",
  "recursive": true
}

Response 202:
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

Scanning is submitted as an async job. The directory path is validated synchronously before submission. Poll `GET /jobs/{job_id}` for status:

```http
GET /jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890

Response 200 (complete):
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "complete",
  "result": {
    "scanned": 47,
    "new": 12,
    "updated": 3,
    "skipped": 32,
    "errors": []
  },
  "error": null
}
```

#### List Videos
```http
GET /videos?limit=20&offset=0&sort=modified_desc

Response 200:
{
  "videos": [
    {
      "id": 1,
      "path": "/home/user/videos/clip1.mp4",
      "filename": "clip1.mp4",
      "duration": 125.5,
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "codec": "h264",
      "thumbnail": "/thumbnails/1.jpg"
    }
  ],
  "total": 47
}
```

### Project Endpoints

#### Create Project
```http
POST /projects
Content-Type: application/json

{
  "name": "My First Montage",
  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  }
}

Response 201:
{
  "id": "proj_abc123",
  "name": "My First Montage",
  "created_at": "2024-01-15T10:30:00Z",
  "output": {...},
  "tracks": [],
  "rust_core_version": "0.1.0"
}
```

### Clip Endpoints

#### Add Clip to Project
```http
POST /projects/proj_abc123/clips
Content-Type: application/json

{
  "source": "/home/user/videos/clip1.mp4",
  "in_point": 10.0,
  "out_point": 25.0
}

Response 201:
{
  "id": "clip_xyz789",
  "source": "/home/user/videos/clip1.mp4",
  "in_point": 10.0,
  "out_point": 25.0,
  "timeline_start": 0,
  "timeline_end": 15.0,
  "duration": 15.0,
  "effects": []
}
```

Timeline positions calculated by Rust core.

### Effects Endpoints

#### List Available Effects (AI Discovery)
```http
GET /effects

Response 200:
{
  "effects": [
    {
      "type": "text_overlay",
      "name": "Text Overlay",
      "description": "Add text with optional fade animation",
      "ai_hint": "Use this to add titles, captions, or labels to video",
      "parameters": {
        "text": {"type": "string", "required": true},
        "position": {"type": "enum", "values": ["center", "top", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"], "default": "center"},
        "font_size": {"type": "integer", "min": 8, "max": 200, "default": 48},
        "font_color": {"type": "string", "default": "white"},
        "start": {"type": "number", "default": 0},
        "duration": {"type": "number"},
        "fade_in": {"type": "number", "default": 0},
        "fade_out": {"type": "number", "default": 0}
      }
    },
    {
      "type": "speed",
      "name": "Speed Control",
      "description": "Change playback speed",
      "ai_hint": "Use this for slow motion (speed < 1) or time-lapse effects (speed > 1)",
      "parameters": {
        "speed": {"type": "number", "min": 0.25, "max": 4.0, "default": 1.0},
        "include_audio": {"type": "boolean", "default": true}
      }
    }
  ]
}
```

#### Add Effect to Clip
```http
POST /projects/proj_abc123/clips/clip_xyz789/effects
Content-Type: application/json

{
  "type": "text_overlay",
  "params": {
    "text": "Chapter 1",
    "position": "center",
    "font_size": 64,
    "start": 0,
    "duration": 3,
    "fade_in": 0.5,
    "fade_out": 0.5
  }
}

Response 201:
{
  "id": "effect_001",
  "type": "text_overlay",
  "params": {...},
  "filter_preview": "drawtext=text='Chapter 1':fontsize=64:..."
}
```

Filter string generated by Rust core.

### Render Endpoints

#### Start Render
```http
POST /render/start
Content-Type: application/json

{
  "project_id": "proj_abc123",
  "output_path": "/home/user/output/montage.mp4",
  "quality": "high"
}

Response 202:
{
  "job_id": "job_render_001",
  "status": "queued",
  "project_id": "proj_abc123",
  "output_path": "/home/user/output/montage.mp4",
  "rust_core_version": "0.1.0"
}
```

#### Check Render Status
```http
GET /render/jobs/job_render_001

Response 200 (in progress):
{
  "job_id": "job_render_001",
  "status": "running",
  "progress": 0.45,
  "eta_seconds": 120,
  "current_frame": 1350,
  "total_frames": 3000
}
```

### Health Endpoints

```http
GET /health/ready

Response 200:
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok"},
    "ffmpeg": {"status": "ok"},
    "rust_core": {"status": "ok", "version": "0.1.0"}
  }
}
```

### System Info (Version Tracking)

```http
GET /system/info

Response 200:
{
  "python_version": "3.11.5",
  "rust_core_version": "0.1.0",
  "ffmpeg_version": "5.1.2",
  "api_version": "1.0.0"
}
```

---

## Error Responses (Structured for Debuggability)

All errors follow a consistent, structured format:

```json
{
  "error": {
    "code": "INVALID_TIME_RANGE",
    "category": "validation",
    "message": "out_point (25.0) must be greater than in_point (30.0)",
    "details": {
      "field": "in_point",
      "in_point": 30.0,
      "out_point": 25.0
    },
    "suggestion": "Set in_point to a value less than 25.0",
    "correlation_id": "req_abc123",
    "rust_error": true
  }
}
```

Errors from Rust core include `rust_error: true` for traceability.

---

## File Structure (Hybrid MVP)

```
ai-video-editor/
├── src/                          # Python source
│   ├── __init__.py
│   ├── main.py                   # FastAPI app with lifespan
│   ├── config.py                 # Pydantic settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── videos.py
│   │   ├── projects.py
│   │   ├── effects.py
│   │   ├── render.py
│   │   ├── health.py             # Includes Rust core health check
│   │   ├── websocket.py          # WebSocket endpoint for GUI events
│   │   └── middleware/
│   │       ├── correlation.py
│   │       ├── metrics.py
│   │       └── error_handler.py  # Handles Rust errors
│   │
│   ├── services/                 # Business logic (injectable)
│   │   ├── __init__.py
│   │   ├── library.py
│   │   ├── timeline.py           # Uses Rust timeline math
│   │   ├── render.py             # Uses Rust command builder
│   │   └── audit.py
│   │
│   ├── ffmpeg/
│   │   ├── __init__.py
│   │   ├── probe.py
│   │   ├── executor.py           # Executes Rust-built commands
│   │   └── integration.py        # Rust core integration
│   │
│   ├── domain/
│   │   ├── models/
│   │   │   ├── video.py
│   │   │   ├── project.py
│   │   │   └── effect.py
│   │   └── logic/                # Delegates to Rust
│   │       └── validation.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── project_storage.py
│   │   └── protocols.py
│   │
│   └── observability/
│       ├── logging.py
│       ├── metrics.py
│       └── correlation.py
│
├── gui/                          # Frontend source (MVP)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   │
│   ├── src/
│   │   ├── main.tsx              # Entry point
│   │   ├── App.tsx               # Application shell
│   │   │
│   │   ├── components/
│   │   │   ├── shell/            # Navigation, status bar
│   │   │   ├── dashboard/        # Health, metrics, activity
│   │   │   ├── library/          # Video grid, search
│   │   │   └── projects/         # Project list, clip list
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useApi.ts
│   │   │
│   │   ├── stores/
│   │   │   └── appStore.ts
│   │   │
│   │   └── api/
│   │       └── client.ts
│   │
│   └── dist/                     # Built output (gitignored)
│
├── rust/                         # Rust source
│   ├── stoat_ferret_core/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs            # PyO3 module
│   │       ├── timeline.rs
│   │       ├── filters.rs
│   │       ├── commands.rs
│   │       └── sanitize.rs
│   └── Cargo.toml                # Workspace
│
├── tests/
│   ├── python/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/             # FFmpeg validation
│   │   ├── fixtures/
│   │   │   ├── fake_ffmpeg.py
│   │   │   └── test_videos/
│   │   └── conftest.py
│   ├── rust/                     # In rust/stoat_ferret_core/src/
│   └── gui/                      # Frontend tests
│       └── e2e/                  # Playwright E2E tests
│
├── stubs/
│   └── stoat_ferret_core.pyi     # Python type stubs
│
├── data/
│   ├── videos.db
│   ├── thumbnails/
│   └── projects/
│
├── Dockerfile                    # Multi-stage: Rust + Python + GUI
├── docker-compose.yml
├── pyproject.toml
├── maturin.toml                  # Rust build config
└── README.md
```

---

## Success Criteria

### Functional Criteria

1. **Library Management**
   - [ ] Can scan a directory (async job with polling via /jobs/{id})
   - [ ] Can search videos by filename
   - [ ] Thumbnails are generated automatically

2. **Timeline Operations**
   - [ ] Can create a project
   - [ ] Can add/remove/reorder clips
   - [ ] Timeline positions calculated by Rust

3. **Effects**
   - [ ] Text overlay (filter built by Rust)
   - [ ] Speed control (filter built by Rust)

4. **Rendering**
   - [ ] Can render timeline (command built by Rust)
   - [ ] Progress trackable via API
   - [ ] Output file is playable

5. **API Quality**
   - [ ] OpenAPI documentation complete
   - [ ] AI-friendly effect discovery
   - [ ] Rust core version visible in responses

### Quality Criteria

6. **Testability**
   - [ ] Rust unit test coverage >90%
   - [ ] Python test coverage >80%
   - [ ] Contract tests for FFmpeg commands
   - [ ] Property-based tests (proptest) for Rust

7. **Observability**
   - [ ] /metrics endpoint working
   - [ ] Structured logs with correlation IDs
   - [ ] Rust core timing metrics

8. **Operability**
   - [ ] /health/ready includes Rust core check
   - [ ] Environment variable config works
   - [ ] Graceful shutdown works

9. **Performance**
   - [ ] Rust filter generation <1ms
   - [ ] Rust timeline calculation <5ms for 100 clips
   - [ ] API response time <200ms (p95)

10. **Security**
    - [ ] Path validation by Rust prevents traversal
    - [ ] Text sanitization by Rust prevents injection
    - [ ] No shell injection possible

### GUI Criteria

11. **Dashboard**
    - [ ] Health status displays correctly
    - [ ] Metrics refresh in real-time
    - [ ] Activity log shows recent events

12. **Library Browser**
    - [ ] Video grid displays thumbnails
    - [ ] Search returns relevant results
    - [ ] Scan progress shows in modal

13. **Project Manager**
    - [ ] Can create new projects
    - [ ] Project list loads correctly
    - [ ] Clip list shows timeline positions

14. **Real-time Updates**
    - [ ] WebSocket connection established
    - [ ] Events display in activity log
    - [ ] Reconnection on disconnect

---

## Getting Started

### Prerequisites

```bash
# Python 3.11+
python --version

# Rust 1.70+ (stable)
rustc --version
cargo --version

# Node.js 18+ (for GUI)
node --version
npm --version

# maturin for PyO3 builds
pip install maturin

# FFmpeg 5.0+
ffmpeg -version
```

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd stoat-and-ferret

# Build Rust core
cd rust/stoat_ferret_core
maturin develop  # Builds and installs to venv
cd ../..

# Install Python dependencies
uv sync

# Install GUI dependencies
cd gui
npm install
cd ..

# Run tests
cargo test --manifest-path rust/Cargo.toml  # Rust tests (fast)
pytest tests/python/                          # Python tests
cd gui && npm test && cd ..                   # GUI tests

# Verify Rust core integration
python -c "import stoat_ferret_core; print(stoat_ferret_core.version())"

# Start development servers (two terminals)
# Terminal 1: Backend
uvicorn src.main:app --reload

# Terminal 2: Frontend (with hot reload)
cd gui && npm run dev
```

### First API Calls

```bash
# Health check (includes Rust core)
curl http://localhost:8000/health/ready

# System info (shows versions)
curl http://localhost:8000/system/info

# Discover effects (for AI integration)
curl http://localhost:8000/effects

# Scan videos (async - returns job ID)
curl -X POST http://localhost:8000/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/videos"}'
# Returns: {"job_id": "..."}

# Poll for scan results
curl http://localhost:8000/jobs/{job_id}
```

---

## Next Steps After MVP

1. Add PIP and split-screen composition (Rust layout engine)
2. Implement audio mixing
3. Add real-time preview with libmpv
4. Enable hardware-accelerated encoding (Rust detection)
5. Add distributed tracing (OpenTelemetry)
6. Expand GUI with Effect Workshop (Phase 2)
7. Add Visual Timeline Canvas (Phase 3)
8. Implement AI Theater Mode for full-screen viewing (Phase 4)

**Quality Reference:** See **07-quality-architecture.md** for detailed implementation patterns.

**GUI Reference:** See **08-gui-architecture.md** for GUI implementation details and AI Theater Mode specification.
