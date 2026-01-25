# stoat-and-ferret - System Architecture

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

This document describes the architecture of an AI-driven video editing system designed for programmatic control. The system uses a **hybrid Python/Rust architecture**: Python (FastAPI) provides the API layer for AI discoverability and rapid iteration, while Rust delivers high-performance compute cores for video processing operations.

**Quality-First Architecture:** Every layer integrates observability, testability, and operability from the foundation up. See **07-quality-architecture.md** for detailed implementation patterns.

**Performance-First Core:** Compute-intensive operations are implemented in Rust and exposed via PyO3, providing native-code speed with Python's ergonomics.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  AI Agent    │  │   Web UI     │  │   CLI Tool   │  │  External    │    │
│  │  (Claude)    │  │  (Future)    │  │              │  │  Systems     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
                              REST API (JSON)
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                      Python API Layer (FastAPI)                              │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                         FastAPI Application                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │  │
│  │  │  /videos   │ │ /projects  │ │  /effects  │ │  /render   │         │  │
│  │  │  /search   │ │  /clips    │ │  /compose  │ │  /preview  │         │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │  Middleware: Correlation ID │ Metrics │ Error Handler │ Auth   │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                    Python Service Layer (Orchestration)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Library    │  │   Timeline   │  │   Effects    │  │   Render     │    │
│  │   Service    │  │   Service    │  │   Service    │  │   Service    │    │
│  │  (injected)  │  │  (injected)  │  │  (injected)  │  │  (injected)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
                               PyO3 Bindings
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                      Rust Core Library (Performance)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    stoat_ferret_core (Rust crate)                     │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │  Timeline  │ │   Filter   │ │  Command   │ │   Render   │        │  │
│  │  │    Math    │ │   Builder  │ │  Builder   │ │Coordinator │        │  │
│  │  │ (pure fn)  │ │ (pure fn)  │ │ (pure fn)  │ │ (stateful) │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │   Input    │ │   Layout   │ │  Hardware  │ │  Progress  │        │  │
│  │  │ Sanitizer  │ │   Engine   │ │ Detection  │ │    ETA     │        │  │
│  │  │ (security) │ │ (geometry) │ │  (encode)  │ │   (calc)   │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                        Processing Layer (Python)                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Subprocess Manager                               │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │  │
│  │  │ FFmpeg Process │  │ FFprobe Query  │  │ Job Executor   │         │  │
│  │  │ (render jobs)  │  │ (metadata)     │  │ (async queue)  │         │  │
│  │  │ +timeout/retry │  │ +caching       │  │ +recovery      │         │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Preview Engine                                 │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │  │
│  │  │ libmpv Player  │  │ Proxy Manager  │  │ Frame Extract  │         │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                         Storage Layer (Python)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   SQLite     │  │   Project    │  │   Media      │  │   Proxy      │    │
│  │  (metadata)  │  │   Files      │  │   Files      │  │   Cache      │    │
│  │  + FTS5      │  │   (JSON)     │  │  (originals) │  │  (transcoded)│    │
│  │  + Audit Log │  │  + Versions  │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────────┐
│                      Cross-Cutting: Observability                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Metrics    │  │  Structured  │  │   Traces     │  │   Health     │    │
│  │  /metrics    │  │    Logs      │  │  (optional)  │  │   Checks     │    │
│  │  Prometheus  │  │   JSON+CID   │  │ OpenTelemetry│  │ /health/*    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Hybrid Architecture Rationale

### Why Python for the API Layer

| Benefit | Explanation |
|---------|-------------|
| **AI Discoverability** | FastAPI generates OpenAPI schemas automatically; AI agents can discover and understand the API |
| **Rapid Iteration** | Hot reload, dynamic typing for quick API changes during development |
| **Rich Ecosystem** | Excellent libraries for REST APIs, validation, async I/O, and observability |
| **Developer Ergonomics** | Easy to read, modify, and extend; familiar to most developers |

### Why Rust for the Compute Core

| Benefit | Explanation |
|---------|-------------|
| **Zero-Cost Abstractions** | High-level code compiles to optimal machine code |
| **Memory Safety** | No garbage collector, no data races, predictable performance |
| **Compile-Time Guarantees** | Input sanitization verified at compile time, not runtime |
| **CPU Parallelism** | Rayon enables effortless parallel iteration for multi-core utilization |
| **FFI Quality** | PyO3 provides excellent Python bindings with minimal overhead |

### Boundary Between Python and Rust

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Rust Core Responsibilities                       │
├─────────────────────────────────────────────────────────────────────────┤
│  • Timeline calculations (positions, durations, overlaps)               │
│  • FFmpeg command generation (filter chains, encoding presets)          │
│  • Input sanitization (text escaping, path validation)                  │
│  • Layout math (PIP positions, split-screen grids)                      │
│  • Render coordination (progress tracking, ETA calculation)             │
│  • Hardware detection (encoder availability)                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       Python Layer Responsibilities                      │
├─────────────────────────────────────────────────────────────────────────┤
│  • HTTP request handling (FastAPI routes, middleware)                   │
│  • API schema generation (OpenAPI, effect discovery)                    │
│  • Subprocess management (FFmpeg execution, libmpv control)             │
│  • Database operations (SQLite, project storage)                        │
│  • Job queue orchestration (arq/Redis)                                  │
│  • Observability (logging, metrics, health checks)                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quality Infrastructure

The architecture integrates quality attributes at every layer. These are not optional additions but fundamental architectural components.

### Observability Stack

```
┌────────────────────────────────────────────────────────────────┐
│                    Observability Flow                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Request → [Correlation ID] → Service → Rust Core → Response  │
│              ↓                    ↓           ↓                │
│          [Metrics]            [Logs]    [Performance]          │
│              ↓                    ↓           ↓                │
│          /metrics          structured    benchmarks            │
│          (Prometheus)      JSON+CID     (Rust timing)          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Metrics (Prometheus format):**
- `video_editor_http_requests_total{method, endpoint, status}`
- `video_editor_http_request_duration_seconds{method, endpoint}`
- `video_editor_render_jobs_total{status}`
- `video_editor_render_duration_seconds{quality}`
- `video_editor_ffmpeg_processes_active`
- `video_editor_rust_core_operation_seconds{operation}` - Rust operation timing
- `video_editor_filter_generation_seconds` - Filter chain build time

**Structured Logs:**
```json
{
  "timestamp": "2024-01-15T12:00:00.123Z",
  "level": "info",
  "event": "render_started",
  "correlation_id": "req_abc123",
  "project_id": "proj_xyz",
  "job_id": "job_001",
  "rust_core_version": "0.1.0"
}
```

**Health Checks:**
- `/health/live` - Is the process running? (liveness probe)
- `/health/ready` - Can it serve requests? Includes Rust core check (readiness probe)
- `/health/startup` - Has initialization completed?

### Testability Architecture

**Dependency Injection Pattern:**
```
┌─────────────────────────────────────────────────────────────────┐
│                  Service Construction                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Production:                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Real FFmpeg  │───→│   Service    │←───│  Rust Core   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
│  Testing (Python Integration):                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Fake FFmpeg  │───→│   Service    │←───│  Rust Core   │      │
│  │ (records     │    │  (same code) │    │ (real impl)  │      │
│  │  commands)   │    └──────────────┘    └──────────────┘      │
│  └──────────────┘                                                │
│                                                                  │
│  Testing (Rust Unit):                                            │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Pure functions tested in isolation with proptest     │       │
│  │  No mocking needed - same inputs always same outputs  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pure Functions in Rust Core:**
- Filter builders (text overlay, speed, transitions)
- Timeline calculations
- Path validation and sanitization
- All testable without mocks
- Property-based testing with proptest

### Operability Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| Externalized config | pydantic-settings + env vars | Change behavior without code |
| Graceful shutdown | Lifespan handler | Complete in-flight work |
| Health checks | Dedicated endpoints (includes Rust check) | Container orchestration |
| Rate limiting | Middleware | Resource protection |
| Rust core versioning | Exposed via API | Track deployed components |

### Security Controls

| Control | Location | Protection |
|---------|----------|------------|
| Path validation | Rust sanitizer | Directory traversal |
| Input sanitization | Rust sanitizer | FFmpeg command injection |
| Subprocess isolation | Python processing layer | Shell injection |
| Audit logging | Python services | Non-repudiation |

---

## Core Components

### 1. Python API Layer

**Technology:** FastAPI (Python)

**Responsibilities:**
- Request validation and parameter coercion
- **Correlation ID injection** (every request gets unique ID)
- **Metrics collection** (request count, duration, status)
- Authentication (optional, for multi-user scenarios)
- Rate limiting and request queuing
- OpenAPI schema generation for AI discovery
- WebSocket support for real-time updates
- **Structured error responses** with recovery suggestions

**Endpoint Groups:**

| Group | Purpose |
|-------|---------|
| `/videos` | Library management (CRUD, scan, search) |
| `/projects` | Project/timeline management |
| `/clips` | Clip operations within projects |
| `/effects` | Effect application and discovery |
| `/compose` | Multi-stream composition (PIP, split) |
| `/render` | Export job management |
| `/preview` | Real-time preview control |

### 2. Python Service Layer

**Design Pattern:** All services use constructor injection for dependencies. This enables testing with fakes/mocks and makes dependencies explicit.

```python
class RenderService:
    def __init__(
        self,
        ffmpeg: FFmpegExecutor,        # Protocol, injectable
        rust_core: StoatFerretCore,    # PyO3 bindings to Rust
        storage: ProjectStorage,        # Protocol, injectable
        metrics: MetricsCollector,      # Protocol, injectable
        logger: StructuredLogger,       # Protocol, injectable
    ):
        # Dependencies are explicit and testable
```

**Library Service**
```
Responsibilities:
├── Directory scanning and file discovery
├── Metadata extraction via FFprobe
├── Thumbnail generation
├── Full-text search indexing
├── Proxy file management
├── Emit metrics: videos_scanned_total
└── Audit log: scan events
```

**Timeline Service**
```
Responsibilities:
├── Project CRUD operations
├── Track/clip management
├── Timeline validation (via Rust core)
├── Effect attachment
├── Project serialization (JSON)
├── Project versioning for recovery
└── Audit log: project modifications
```

**Effects Service**
```
Responsibilities:
├── Effect parameter validation (via Rust core)
├── Filter expression generation (via Rust core)
├── Effect composition/chaining
├── Available effects discovery
├── Default parameter generation
└── Emit metrics: effects_applied_total by type
```

**Render Service**
```
Responsibilities:
├── Timeline to FFmpeg command translation (via Rust core)
├── Job queue management with recovery
├── Progress tracking with metrics (Rust ETA calculation)
├── Hardware encoder selection (Rust detection)
├── Output format handling
├── Emit metrics: render_jobs_total, render_duration_seconds
└── Audit log: render events
```

### 3. Rust Core Library

The performance-critical heart of the system. All compute-intensive operations are implemented here with compile-time safety guarantees.

**Module Structure:**

```rust
// stoat_ferret_core/src/lib.rs
pub mod timeline;      // Timeline math, position calculations
pub mod filters;       // FFmpeg filter chain building
pub mod commands;      // FFmpeg command construction
pub mod sanitize;      // Input validation and escaping
pub mod layout;        // PIP, split-screen geometry
pub mod render;        // Render coordination, progress tracking
pub mod hardware;      // Encoder detection
```

**Timeline Module (Pure Functions):**
```rust
/// Calculate timeline positions for sequential clips.
/// Pure function - no side effects, fully deterministic.
pub fn calculate_clip_positions(clips: &[ClipInput]) -> Vec<ClipWithPosition> {
    let mut result = Vec::with_capacity(clips.len());
    let mut current_position = 0.0;

    for clip in clips {
        let duration = clip.out_point - clip.in_point;
        result.push(ClipWithPosition {
            clip: clip.clone(),
            timeline_start: current_position,
            timeline_end: current_position + duration,
        });
        current_position += duration;
    }

    result
}

/// Validate time range with detailed error.
pub fn validate_time_range(in_point: f64, out_point: f64, duration: f64) -> Result<(), TimeRangeError> {
    if in_point < 0.0 {
        return Err(TimeRangeError::NegativeInPoint { value: in_point });
    }
    if out_point <= in_point {
        return Err(TimeRangeError::OutBeforeIn { in_point, out_point });
    }
    if out_point > duration {
        return Err(TimeRangeError::OutBeyondDuration { out_point, duration });
    }
    Ok(())
}
```

**Filter Builder Module (Pure Functions):**
```rust
/// Build FFmpeg drawtext filter string.
/// Pure function - no side effects, fully deterministic.
/// Text is sanitized to prevent command injection.
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> String {
    let sanitized_text = sanitize::escape_ffmpeg_text(&params.text);
    let (x, y) = params.position.to_coordinates();
    let alpha_expr = build_alpha_expression(
        params.start,
        params.start + params.duration,
        params.fade_in,
        params.fade_out,
    );
    let enable_expr = format!("between(t,{},{})", params.start, params.start + params.duration);

    format!(
        "drawtext=text='{}':fontsize={}:fontcolor={}:x={}:y={}:enable='{}':alpha='{}'",
        sanitized_text, params.font_size, params.font_color, x, y, enable_expr, alpha_expr
    )
}

/// Build filter chain for concatenation.
pub fn build_concat_filter_chain(
    inputs: &[ConcatInput],
    output_settings: &OutputSettings,
) -> FilterChain {
    // Build complex filter graph with scale, pad, format normalization
    // Returns validated filter chain structure
}
```

**Sanitization Module (Security):**
```rust
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

/// Validate path is within allowed directories.
/// Returns error with details if path escapes allowed roots.
pub fn validate_path(user_path: &Path, allowed_roots: &[PathBuf]) -> Result<PathBuf, PathValidationError> {
    let resolved = user_path.canonicalize()
        .map_err(|e| PathValidationError::CannotResolve {
            path: user_path.to_path_buf(),
            reason: e.to_string()
        })?;

    for root in allowed_roots {
        if resolved.starts_with(root) {
            return Ok(resolved);
        }
    }

    Err(PathValidationError::OutsideAllowedRoots {
        path: user_path.to_path_buf(),
        allowed: allowed_roots.to_vec(),
    })
}
```

**PyO3 Bindings:**
```rust
use pyo3::prelude::*;

#[pymodule]
fn stoat_ferret_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_calculate_clip_positions, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_text_overlay_filter, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_path, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_concat_command, m)?)?;
    m.add_class::<PyTextOverlayParams>()?;
    m.add_class::<PyOutputSettings>()?;
    Ok(())
}

#[pyfunction]
fn py_build_text_overlay_filter(params: PyTextOverlayParams) -> PyResult<String> {
    Ok(filters::build_text_overlay_filter(&params.into()))
}
```

**Testing Strategy for Rust Core:**
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Property-based test: filter generation never panics
    proptest! {
        #[test]
        fn text_overlay_never_panics(
            text in ".*",
            font_size in 8u32..500,
            start in 0.0f64..1000.0,
            duration in 0.1f64..100.0,
        ) {
            let params = TextOverlayParams {
                text,
                font_size,
                start,
                duration,
                ..Default::default()
            };
            // Should never panic regardless of input
            let _ = build_text_overlay_filter(&params);
        }
    }

    // Property-based test: escaped text contains no unescaped special chars
    proptest! {
        #[test]
        fn escape_removes_dangerous_chars(text in ".*") {
            let escaped = escape_ffmpeg_text(&text);
            // No unescaped single quotes
            assert!(!escaped.contains("'") || escaped.contains("'\\''"));
            // No unescaped colons
            assert!(!escaped.contains(":") || escaped.contains("\\:"));
        }
    }

    #[test]
    fn timeline_positions_are_sequential() {
        let clips = vec![
            ClipInput { in_point: 0.0, out_point: 10.0, .. },
            ClipInput { in_point: 5.0, out_point: 15.0, .. },
        ];
        let result = calculate_clip_positions(&clips);

        assert_eq!(result[0].timeline_start, 0.0);
        assert_eq!(result[0].timeline_end, 10.0);
        assert_eq!(result[1].timeline_start, 10.0);
        assert_eq!(result[1].timeline_end, 20.0);
    }
}
```

### 4. Processing Layer

**Subprocess Manager (Python)**

Wraps FFmpeg/FFprobe execution with reliability and observability:
- Proper stdin/stdout/stderr handling
- **Timeout management** with configurable limits
- **Automatic retry** for transient failures
- Progress parsing from FFmpeg output
- **Structured error handling** with context preservation
- Resource cleanup on failure
- **Metrics emission** (process count, duration, exit codes)
- **Command logging** for debugging and transparency
- **Integration with Rust command builder** for command generation

```python
class FFmpegExecutor(Protocol):
    """Protocol enables dependency injection and testing."""

    async def execute(
        self,
        command: FFmpegCommand,  # Generated by Rust core
        timeout: float | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> FFmpegResult: ...
```

**Job Queue (Python)**

For long-running render operations with full reliability:
- Async task processing (recommend: `arq` with Redis)
- **Job recovery on restart** - interrupted jobs can resume or be marked failed
- Job status persistence with history
- Progress percentage calculation (using Rust ETA module)
- Cancellation support with cleanup
- Webhook callbacks on completion
- **Metrics:** queue_depth, job_duration, success_rate

**Preview Engine (Python)**

Real-time playback using libmpv:
- Python bindings via `python-mpv`
- Filter pipeline for live effect preview
- Seek/scrub with frame accuracy
- Automatic proxy switching
- **Performance metrics** (frame drops, latency)

### 5. Storage Layer

**Design Pattern:** Storage uses repository pattern with protocol interfaces for testability.

```python
class ProjectStorage(Protocol):
    """Injectable storage interface - real or in-memory for tests."""
    async def save(self, project: Project) -> None: ...
    async def load(self, project_id: str) -> Project: ...
    async def delete(self, project_id: str) -> None: ...
    async def list_all(self) -> list[ProjectSummary]: ...
```

**SQLite Database Schema**

```sql
-- Video library
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    duration REAL,
    width INTEGER,
    height INTEGER,
    fps REAL,
    codec TEXT,
    bitrate INTEGER,
    file_size INTEGER,
    created_at TEXT,
    scanned_at TEXT,
    thumbnail_path TEXT,
    proxy_path TEXT,
    metadata JSON
);

-- Full-text search
CREATE VIRTUAL TABLE videos_fts USING fts5(
    filename, path, metadata,
    content='videos',
    content_rowid='id'
);

-- Render jobs with recovery support
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed, cancelled
    progress REAL,
    output_path TEXT,
    error_message TEXT,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    last_checkpoint TEXT,   -- For recovery
    retry_count INTEGER DEFAULT 0,
    rust_core_version TEXT  -- Track which Rust version processed this
);

-- Audit log for debuggability and compliance
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    actor TEXT,
    correlation_id TEXT,
    details JSON
);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_correlation ON audit_log(correlation_id);
```

**Project Files (JSON) with Versioning**

Stored as individual JSON files with version history for recovery:
- Version control friendliness
- Human readability
- Easy backup/restore
- AI parseability
- **Automatic versioning** for recovery from corruption

```
projects/
├── my-video-project/
│   ├── project.json      # Current version
│   ├── .versions/        # Previous versions for recovery
│   │   ├── v001.json
│   │   ├── v002.json
│   │   └── v003.json
│   ├── assets.json       # Asset manifest
│   └── renders/          # Render output directory
```

---

## Data Models

### Timeline Model

```json
{
  "id": "uuid",
  "name": "My Video Project",
  "created_at": "2024-01-15T10:30:00Z",
  "modified_at": "2024-01-15T14:22:00Z",

  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "sample_rate": 48000
  },

  "tracks": [
    {
      "id": "video-main",
      "type": "video",
      "clips": [
        {
          "id": "clip-1",
          "source": "/path/to/video.mp4",
          "in_point": 10.5,
          "out_point": 25.0,
          "timeline_start": 0,
          "timeline_end": 14.5,
          "effects": [
            {
              "type": "text_overlay",
              "params": {
                "text": "Introduction",
                "position": "center",
                "font_size": 48,
                "start": 0,
                "duration": 3,
                "fade_in": 0.5,
                "fade_out": 0.5
              }
            }
          ]
        }
      ]
    },
    {
      "id": "audio-music",
      "type": "audio",
      "clips": [
        {
          "id": "music-1",
          "source": "/path/to/music.mp3",
          "in_point": 0,
          "out_point": 120,
          "timeline_start": 0,
          "volume": 0.3
        }
      ]
    }
  ],

  "global_effects": [
    {
      "type": "fade_out",
      "params": {
        "duration": 1.0
      }
    }
  ]
}
```

### Effect Definition Schema

Effect schemas are defined to support AI discovery. The Rust core validates parameters while Python exposes the discovery API.

```json
{
  "effect_type": "text_overlay",
  "display_name": "Text Overlay",
  "description": "Add text with optional fade animation",
  "category": "overlay",
  "ai_hint": "Use this to add titles, captions, or labels to video",
  "parameters": {
    "text": {
      "type": "string",
      "required": true,
      "description": "Text to display"
    },
    "position": {
      "type": "enum",
      "values": ["center", "top", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"],
      "default": "center"
    },
    "font_size": {
      "type": "integer",
      "min": 8,
      "max": 500,
      "default": 48
    },
    "font_color": {
      "type": "string",
      "format": "color",
      "default": "white"
    },
    "start": {
      "type": "number",
      "min": 0,
      "description": "Start time in seconds relative to clip"
    },
    "duration": {
      "type": "number",
      "min": 0,
      "description": "Duration in seconds"
    },
    "fade_in": {
      "type": "number",
      "min": 0,
      "default": 0
    },
    "fade_out": {
      "type": "number",
      "min": 0,
      "default": 0
    }
  }
}
```

---

## Data Flow

### Video Import Flow

```
User Request                API Layer              Service Layer           Storage
     │                          │                        │                    │
     │  POST /videos/scan       │                        │                    │
     │  {path: "/media"}        │                        │                    │
     ├─────────────────────────>│                        │                    │
     │                          │  scan_directory()      │                    │
     │                          ├───────────────────────>│                    │
     │                          │                        │  validate_path()   │
     │                          │                        │  (Rust core)       │
     │                          │                        │  find video files  │
     │                          │                        ├───────────────────>│
     │                          │                        │<───────────────────┤
     │                          │                        │                    │
     │                          │                        │  for each file:    │
     │                          │                        │  - ffprobe metadata│
     │                          │                        │  - generate thumb  │
     │                          │                        │  - insert to DB    │
     │                          │                        ├───────────────────>│
     │                          │                        │<───────────────────┤
     │                          │<───────────────────────┤                    │
     │  {scanned: 47, new: 12}  │                        │                    │
     │<─────────────────────────┤                        │                    │
```

### Render Flow with Rust Core

```
User Request              API Layer            Service Layer         Rust Core           FFmpeg
     │                        │                      │                   │                  │
     │  POST /render/start    │                      │                   │                  │
     │  {project_id: "..."}   │                      │                   │                  │
     ├───────────────────────>│                      │                   │                  │
     │                        │  start_render()      │                   │                  │
     │                        ├─────────────────────>│                   │                  │
     │                        │                      │  build_command()  │                  │
     │                        │                      ├──────────────────>│                  │
     │                        │                      │  [filter chains,  │                  │
     │                        │                      │   encoding args,  │                  │
     │                        │                      │   validation]     │                  │
     │                        │                      │<──────────────────┤                  │
     │                        │                      │                   │                  │
     │                        │                      │  enqueue_job()    │                  │
     │                        │                      │                   │                  │
     │                        │<─────────────────────┤                   │                  │
     │  {job_id: "abc123"}    │                      │                   │                  │
     │<───────────────────────┤                      │                   │                  │
     │                        │                      │                   │                  │
     │                        │              [Background Job Executor]   │                  │
     │                        │                      │                   │                  │
     │                        │                      │  execute_ffmpeg() │                  │
     │                        │                      ├─────────────────────────────────────>│
     │                        │                      │                   │  [processing]    │
     │                        │                      │  calc_progress()  │                  │
     │                        │                      ├──────────────────>│                  │
     │                        │                      │<──────────────────┤                  │
     │                        │                      │<─────────────────────────────────────┤
     │                        │                      │                   │                  │
     │  [Webhook callback]    │                      │                   │                  │
     │<─────────────────────────────────────────────────────────────────────────────────────
```

---

## Security Architecture

Security is designed-in from the foundation, with Rust providing compile-time safety guarantees for critical paths.

### Defense in Depth

| Layer | Control | Protection Against | Implementation |
|-------|---------|-------------------|----------------|
| API | Input validation | Malformed requests | Pydantic (Python) |
| API | Rate limiting | DoS, abuse | Middleware (Python) |
| Service | Path validation | Directory traversal | **Rust sanitizer** |
| Service | Audit logging | Non-repudiation | Python |
| FFmpeg | Input sanitization | Command injection | **Rust sanitizer** |
| FFmpeg | Subprocess isolation | Shell injection | Python (never shell=True) |
| Storage | Access control | Unauthorized access | Python |

### Rust Security Guarantees

**Path Traversal Prevention (Rust):**
```rust
/// Validate path is within allowed directories.
/// Compile-time guarantee: this function must be called before any path is used.
pub fn validate_path(user_path: &Path, allowed_roots: &[PathBuf]) -> Result<PathBuf, PathValidationError> {
    let resolved = user_path.canonicalize()
        .map_err(|e| PathValidationError::CannotResolve {
            path: user_path.to_path_buf(),
            reason: e.to_string()
        })?;

    for root in allowed_roots {
        if resolved.starts_with(root) {
            return Ok(resolved);
        }
    }

    Err(PathValidationError::OutsideAllowedRoots {
        path: user_path.to_path_buf(),
        allowed: allowed_roots.to_vec(),
    })
}
```

**FFmpeg Text Sanitization (Rust):**
```rust
/// Escape text for safe FFmpeg filter usage.
/// No possibility of command injection when using escaped text.
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
```

### Resource Protection

- Render job limits per user/session
- Disk space monitoring with pre-render check (Rust)
- FFmpeg process timeout enforcement
- Memory limits via cgroups (optional)
- **Queue depth limits** to prevent resource exhaustion

---

## Scalability Considerations

### Current Design (Solo Use)
- SQLite handles concurrent reads well
- Single FFmpeg process per render
- In-process preview (libmpv)
- Rust core provides efficient single-threaded performance

### Future Scaling Options
- PostgreSQL for multi-user scenarios
- Distributed job queue (Redis + workers)
- Render farm with job distribution
- CDN integration for output delivery
- **Rust core enables efficient scaling** - no GIL limitations for compute

---

## Directory Structure

```
ai-video-editor/
├── src/                          # Python source
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app with lifespan
│   │   ├── routes/
│   │   │   ├── videos.py
│   │   │   ├── projects.py
│   │   │   ├── effects.py
│   │   │   ├── render.py
│   │   │   ├── preview.py
│   │   │   └── health.py        # Health check endpoints
│   │   ├── middleware/
│   │   │   ├── correlation.py   # Correlation ID injection
│   │   │   ├── metrics.py       # Request metrics
│   │   │   └── error_handler.py # Structured error responses
│   │   └── schemas/
│   │       ├── video.py
│   │       ├── project.py
│   │       ├── effect.py
│   │       └── error.py         # Structured error schema
│   │
│   ├── services/                # Business logic (injectable)
│   │   ├── library.py
│   │   ├── timeline.py
│   │   ├── effects.py
│   │   └── render.py
│   │
│   ├── domain/                  # Pure business logic (Python side)
│   │   ├── models/              # Domain entities
│   │   │   ├── video.py
│   │   │   ├── project.py
│   │   │   ├── clip.py
│   │   │   └── effect.py
│   │   └── logic/               # Python-side logic (delegates to Rust)
│   │       └── validation.py
│   │
│   ├── ffmpeg/
│   │   ├── __init__.py
│   │   ├── probe.py             # FFprobe wrapper
│   │   ├── executor.py          # Subprocess execution (protocol)
│   │   └── integration.py       # Integration with Rust command builder
│   │
│   ├── infrastructure/          # External interfaces
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── migrations/
│   │   │   └── repositories.py
│   │   ├── storage/
│   │   │   ├── project_storage.py
│   │   │   └── file_storage.py
│   │   └── queue/
│   │       └── render_queue.py
│   │
│   ├── observability/           # Cross-cutting concerns
│   │   ├── logging.py           # Structured logging setup
│   │   ├── metrics.py           # Prometheus metrics
│   │   ├── tracing.py           # OpenTelemetry (optional)
│   │   └── audit.py             # Audit logging
│   │
│   ├── preview/
│   │   ├── player.py            # libmpv integration
│   │   └── proxy.py             # Proxy management
│   │
│   └── config.py                # Pydantic settings
│
├── rust/                         # Rust source
│   ├── stoat_ferret_core/        # Main Rust crate
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs           # PyO3 module definition
│   │       ├── timeline.rs      # Timeline calculations
│   │       ├── filters.rs       # Filter builders
│   │       ├── commands.rs      # FFmpeg command construction
│   │       ├── sanitize.rs      # Input validation/escaping
│   │       ├── layout.rs        # PIP, split-screen geometry
│   │       ├── render.rs        # Render coordination
│   │       ├── hardware.rs      # Encoder detection
│   │       └── errors.rs        # Error types
│   └── Cargo.toml               # Workspace definition
│
├── tests/
│   ├── python/
│   │   ├── unit/                # Fast, isolated Python tests
│   │   ├── integration/         # API + real dependencies
│   │   ├── contract/            # FFmpeg command validation
│   │   ├── smoke/               # Post-deployment checks
│   │   └── conftest.py          # Shared fixtures
│   └── rust/                    # Rust tests (in rust/stoat_ferret_core/src/)
│
├── stubs/
│   └── stoat_ferret_core.pyi    # Python type stubs for Rust module
│
├── projects/                     # User project storage
├── cache/
│   ├── thumbnails/
│   └── proxies/
├── Dockerfile                   # Production container (Python + Rust)
├── docker-compose.yml           # Local development
├── pyproject.toml               # Python dependencies + tool config
└── maturin.toml                 # Rust build configuration
```

---

## Integration Points

### AI Agent Integration

The API is designed for natural language to API call translation. Python/FastAPI provides the AI-discoverable interface, while Rust provides the performance.

```
User: "Add a title 'Chapter 1' that fades in at the start of the video"

AI translates to:
POST /effects/text
{
  "clip_id": "main-video",
  "text": "Chapter 1",
  "position": "center",
  "start": 0,
  "duration": 5,
  "fade_in": 1.0,
  "fade_out": 0.5
}

→ Python validates request via Pydantic
→ Rust core builds filter: "drawtext=text='Chapter 1':..."
→ Python stores effect on clip
```

### Discovery Endpoints for AI

```
GET /effects
Returns: List of all available effects with their parameter schemas

GET /effects/{effect_type}/schema
Returns: JSON Schema for effect parameters

GET /compose/layouts
Returns: Available composition layouts (pip, split-screen variants)

GET /system/info
Returns: System info including Rust core version
```

---

## Non-Functional Requirements

### Performance Targets

| Requirement | Target | Measurement | Component |
|-------------|--------|-------------|-----------|
| API Response Time | <100ms (p95) | `http_request_duration_seconds` histogram | Python |
| Filter Generation | <1ms | `rust_filter_generation_seconds` histogram | Rust |
| Timeline Calculation | <5ms for 100 clips | `rust_timeline_calculation_seconds` histogram | Rust |
| Preview Latency | <100ms seek response | `preview_seek_latency_seconds` histogram | Python + libmpv |
| Render Throughput | >1x realtime with HW accel | `render_duration_seconds` / video duration | Rust coordinator |
| Database Size | Support 100K+ videos | Load test with synthetic data | Python |

### Reliability Targets (SLIs)

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| API Availability | >99.9% | Health check success rate |
| Render Success Rate | >95% | `render_jobs_total{status="completed"}` / total |
| Error Rate | <1% | 5xx responses / total requests |
| Data Durability | Zero loss | Project versioning + backups |

### Operability Requirements

| Requirement | Implementation |
|-------------|---------------|
| Configuration | Externalized via environment variables |
| Logging | Structured JSON with correlation IDs |
| Metrics | Prometheus format at /metrics |
| Health Checks | /health/live, /health/ready (includes Rust check) |
| Graceful Shutdown | Complete in-flight work within 30s |
| Recovery | Jobs resume or marked failed on restart |
| Version Tracking | Python and Rust core versions in /system/info |

### Quality Attributes Summary

See **07-quality-architecture.md** for complete implementation details.

| Attribute | Key Implementation |
|-----------|-------------------|
| Testability | Dependency injection, pure Rust functions, >80% coverage |
| Observability | Metrics, structured logs, traces, health checks |
| Operability | Externalized config, graceful shutdown, feature flags |
| Debuggability | Structured errors, correlation IDs, audit trail |
| Maintainability | Clear Python/Rust boundaries, explicit dependencies |
| Deployability | Multi-stage containers, smoke tests, rollback capability |
| Reliability | Retries, job recovery, data versioning |
| Security | Rust path validation, Rust input sanitization, audit logging |
