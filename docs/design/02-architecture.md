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
│  │  (Claude)    │  │ (React SPA)  │  │              │  │  Systems     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
                          REST API (JSON) + WebSocket
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                      Python API Layer (FastAPI)                              │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                         FastAPI Application                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │  │
│  │  │  /videos   │ │ /projects  │ │  /effects  │ │  /render   │         │  │
│  │  │  /search   │ │  /clips    │ │  /compose  │ │  /preview  │         │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │  │
│  │  ┌────────────┐ ┌────────────┐                                       │  │
│  │  │  /ws       │ │ /gui       │                                       │  │
│  │  │ (WebSocket)│ │ (static)   │                                       │  │
│  │  └────────────┘ └────────────┘                                       │  │
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
│  • FFmpeg expression engine (type-safe expression tree builder)         │
│  • Drawtext filter builder (text overlays with position presets)        │
│  • Speed control filters (setpts + auto-chained atempo)                │
│  • Audio mixing filters (volume, afade, amix, ducking)                 │
│  • Transition filters (fade, xfade, acrossfade)                        │
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
│  • Job queue orchestration (asyncio.Queue)                              │
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
- `http_requests_total{method, path, status}` - HTTP request counter
- `http_request_duration_seconds{method, path}` - HTTP request duration histogram
- `stoat_ferret_effect_applications_total{effect_type}` - Effect applications by type
- `stoat_ferret_transition_applications_total{transition_type}` - Transition applications by type
- `stoat_ferret_ffmpeg_executions_total{status}` - FFmpeg execution counter
- `stoat_ferret_ffmpeg_execution_duration_seconds` - FFmpeg execution duration histogram
- `stoat_ferret_ffmpeg_active_processes` - Active FFmpeg process gauge

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
- Expression engine (`Expr` tree builder with arity validation)
- `DrawtextBuilder` (text overlay with position presets, alpha fades)
- `SpeedControl` (setpts + auto-chained atempo filters)
- `VolumeBuilder`, `AfadeBuilder`, `AmixBuilder`, `DuckingPattern` (audio mixing)
- `FadeBuilder`, `XfadeBuilder`, `AcrossfadeBuilder` (transitions)
- Filter types (`Filter`, `FilterChain`, `FilterGraph`)
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
| `/jobs` | Async job status polling |
| `/projects` | Project/timeline management |
| `/clips` | Clip operations within projects |
| `/effects` | Effect application and discovery |
| `/compose` | Multi-stream composition (PIP, split) |
| `/render` | Export job management |
| `/preview` | Real-time preview control |
| `/ws` | WebSocket endpoint for real-time event streaming |
| `/gui` | Static file serving for the React frontend |

**WebSocket Transport Layer:**

The `/ws` endpoint provides real-time event streaming to connected clients using a `ConnectionManager` that tracks active connections and broadcasts events. Supported event types include `HEARTBEAT`, `SCAN_STARTED`, `SCAN_COMPLETED`, `PROJECT_CREATED`, and `HEALTH_STATUS`. A configurable heartbeat interval (default 30s) keeps connections alive.

**Frontend Static Serving:**

Built React/TypeScript frontend assets are served from `/gui` via FastAPI's `StaticFiles` mount with `html=True` for SPA client-side routing support. The mount path is configurable via the `STOAT_GUI_STATIC_PATH` setting.

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

Uses an `EffectRegistry` to manage effect definitions and delegates filter generation to Rust builders via a `build_fn` dispatch pattern.

```
Responsibilities:
├── Effect discovery (GET /effects returns all registered effects with schemas)
├── Effect application (POST to clip, persists in effects_json)
├── Transition application (POST /effects/transition between adjacent clips)
├── Filter string generation via build_fn dispatch to Rust builders
├── Parameter validation against JSON Schema (Draft7Validator)
├── AI hint metadata per effect for agent integration
├── Prometheus metrics (effect_applications_total, transition_applications_total)
└── Registry: EffectRegistry with register/get/list_all/validate pattern

Registry Architecture:
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  EffectRegistry  │────>│ EffectDefinition │────>│  build_fn()      │
│  register()      │     │  name            │     │  (dispatches to  │
│  get()           │     │  description     │     │   Rust builder)  │
│  list_all()      │     │  parameter_schema│     └──────────────────┘
│  validate()      │     │  ai_hints        │     ┌──────────────────┐
└──────────────────┘     │  preview_fn      │────>│  preview_fn()    │
                         │  build_fn        │     │  (sample output) │
                         └──────────────────┘     └──────────────────┘

Registered effects (v007):
├── text_overlay  → DrawtextBuilder (Rust)
├── speed_control → SpeedControl (Rust)
├── audio_mix     → AmixBuilder (Rust)
├── volume        → VolumeBuilder (Rust)
├── audio_fade    → AfadeBuilder (Rust)
├── audio_ducking → DuckingPattern (Rust)
├── video_fade    → FadeBuilder (Rust)
├── xfade         → XfadeBuilder + TransitionType (Rust)
└── acrossfade    → AcrossfadeBuilder (Rust)
```

The registry is injected via `app.state.effect_registry` (DI pattern). Each `EffectDefinition` includes both a `preview_fn` (produces a sample filter string) and a `build_fn` (generates the actual filter from user parameters by dispatching to the corresponding Rust builder). Parameter validation uses `jsonschema.Draft7Validator` against the definition's `parameter_schema`.

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
pub mod ffmpeg;        // FFmpeg filter/command modules (submodules below)
pub mod sanitize;      // Input validation and escaping
pub mod layout;        // PIP, split-screen geometry
pub mod render;        // Render coordination, progress tracking
pub mod hardware;      // Encoder detection

// stoat_ferret_core/src/ffmpeg/
pub mod filter;        // Filter, FilterChain, FilterGraph types
pub mod expression;    // Type-safe FFmpeg expression tree builder
pub mod drawtext;      // DrawtextBuilder for text overlay filters
pub mod speed;         // SpeedControl for setpts/atempo filters
pub mod audio;         // Audio mixing builders (VolumeBuilder, AfadeBuilder, AmixBuilder, DuckingPattern)
pub mod transitions;   // Transition builders (FadeBuilder, XfadeBuilder, AcrossfadeBuilder)
pub mod commands;      // FFmpeg command construction
```

**Expression Module (`ffmpeg/expression.rs`):**

Type-safe builder for FFmpeg filter expressions (alpha curves, enable conditions, timing). Expressions are represented as an algebraic tree that serializes to valid FFmpeg syntax.

```rust
/// Expression tree for FFmpeg filter expressions.
pub enum Expr {
    Const(f64),
    Var(Variable),                             // t, n, w, h, text_w, etc.
    BinaryOp(BinaryOp, Box<Expr>, Box<Expr>),  // +, -, *, /, ^
    UnaryOp(UnaryOp, Box<Expr>),               // negation
    Func(FuncName, Vec<Expr>),                  // between, if, lt, gt, etc.
}

// Builder API with operator overloading:
let fade_in = Expr::if_then_else(
    Expr::lt(Expr::var(Variable::T), Expr::constant(2.0)),
    Expr::var(Variable::T) / Expr::constant(2.0),
    Expr::constant(1.0),
);
// Serializes to: "if(lt(t,2),t/2,1)"
```

Supports 14 FFmpeg functions (`between`, `if`, `lt`, `gt`, `eq`, `gte`, `lte`, `clip`, `abs`, `min`, `max`, `mod`, `not`, `ifnot`) with arity validation. Integers render without decimals (`5.0` → `"5"`).

**Drawtext Builder Module (`ffmpeg/drawtext.rs`):**

Type-safe builder for FFmpeg `drawtext` filters with automatic text escaping and position presets.

```rust
let filter = DrawtextBuilder::new("Chapter 1: Introduction")
    .fontsize(64)
    .fontcolor("white")
    .position(Position::Center)
    .alpha_fade(0.0, 1.0, 5.0, 0.5)  // Uses expression engine
    .build();
// Produces: drawtext=text='Chapter 1\: Introduction':fontsize=64:fontcolor=white:...
```

Position presets: `Center`, `BottomCenter`, `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight` (with configurable margin), and `Absolute { x, y }`. Text is automatically escaped for FFmpeg safety (`:`, `'`, `\`, `%`, `[`, `]`, `;`).

**Speed Control Module (`ffmpeg/speed.rs`):**

Generates `setpts` (video) and `atempo` (audio) filters with automatic chaining for speeds outside the `[0.5, 2.0]` range.

```rust
let ctrl = SpeedControl::new(3.0)?;  // Validates [0.25, 4.0] range
ctrl.setpts_filter();    // setpts=0.333333*PTS
ctrl.atempo_filters();   // [atempo=2, atempo=1.5]  (product = 3.0)
```

The `atempo_chain` algorithm automatically decomposes speeds outside FFmpeg's `[0.5, 2.0]` per-filter limit into a chain of filters whose product equals the target speed.

**Audio Module (`ffmpeg/audio.rs`):**

Builders for audio mixing and processing filters, all exposed via PyO3.

```rust
// Volume control (linear or dB)
let vol = VolumeBuilder::new(0.8)?.build();           // volume=0.8
let vol = VolumeBuilder::from_db("-3dB")?.build();    // volume=-3dB

// Audio fade in/out with curve support
let fade = AfadeBuilder::new("in", 2.0)?
    .start_time(1.0)
    .curve("tri")
    .build();                                          // afade=t=in:d=2:st=1:curve=tri

// Multi-input audio mixing (2-32 inputs)
let mix = AmixBuilder::new(3)?
    .duration_mode("longest")
    .weights(vec![1.0, 0.5, 0.3])
    .normalize(false)
    .build();                                          // amix=inputs=3:duration=longest:...

// Ducking pattern (FilterGraph: asplit + sidechaincompress + anull)
let duck = DuckingPattern::new()
    .threshold(0.05)
    .ratio(4.0)
    .attack(0.01)
    .release(0.3)
    .build();                                          // Returns FilterGraph
```

Supported fade curves: `tri`, `qsin`, `hsin`, `esin`, `log`, `ipar`, `qua`, `cub`, `squ`, `cbr`, `par`.

**Transitions Module (`ffmpeg/transitions.rs`):**

Builders for video and audio transition filters, with `TransitionType` covering all 59 FFmpeg xfade transitions.

```rust
// Video fade in/out
let fade = FadeBuilder::new("in", 1.5)?
    .color("black")
    .build();                                          // fade=t=in:d=1.5:c=black

// Video crossfade (xfade) with named transition type
let xf = XfadeBuilder::new(TransitionType::Dissolve, 1.0, 5.0)?
    .build();                                          // xfade=transition=dissolve:duration=1:offset=5

// Audio crossfade
let acf = AcrossfadeBuilder::new(1.0)?
    .curve1("tri")
    .curve2("tri")
    .overlap(true)
    .build();                                          // acrossfade=d=1:c1=tri:c2=tri:o=1
```

`TransitionType` supports 59 named transitions including `Fade`, `Dissolve`, `Wipeleft`, `Circleopen`, `Radial`, `Pixelize`, `Hblur`, and more. Conversion via `TransitionType::from_str(name)`.

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

**Filter Module (`ffmpeg/filter.rs`):**

Core filter types used as output by all builders:

```rust
/// A single FFmpeg filter with named parameters.
pub struct Filter { name: String, params: Vec<(String, String)> }
/// A semicolon-separated sequence of filters.
pub struct FilterChain { filters: Vec<Filter> }
/// A complete filter graph (comma-separated chains).
pub struct FilterGraph { chains: Vec<FilterChain> }

// Usage example from DrawtextBuilder:
let filter = Filter::new("drawtext")
    .param("text", "'Chapter 1\\: Intro'")
    .param("fontsize", "64")
    .param("fontcolor", "white");
// Renders: drawtext=text='Chapter 1\: Intro':fontsize=64:fontcolor=white
```

`DrawtextBuilder::build()` and `SpeedControl::setpts_filter()` return `Filter` instances. `SpeedControl::atempo_filters()` returns `Vec<Filter>` for chaining.

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

The `_core` module exposes Rust types to Python via PyO3:

```rust
use pyo3::prelude::*;

#[pymodule]
fn _core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Filter types
    m.add_class::<Filter>()?;
    m.add_class::<FilterChain>()?;
    m.add_class::<FilterGraph>()?;
    m.add_class::<FFmpegCommand>()?;

    // Expression engine
    m.add_class::<PyExpr>()?;            // Expr - FFmpeg expression builder

    // Effect builders
    m.add_class::<DrawtextBuilder>()?;   // Drawtext filter builder
    m.add_class::<SpeedControl>()?;      // Speed control (setpts + atempo)

    // Audio mixing builders (v007)
    m.add_class::<VolumeBuilder>()?;     // Volume control (linear/dB)
    m.add_class::<AfadeBuilder>()?;      // Audio fade in/out
    m.add_class::<AmixBuilder>()?;       // Multi-input audio mixing
    m.add_class::<DuckingPattern>()?;    // Sidechain ducking (FilterGraph)

    // Transition builders (v007)
    m.add_class::<TransitionType>()?;    // 59 named xfade transition types
    m.add_class::<FadeBuilder>()?;       // Video fade in/out
    m.add_class::<XfadeBuilder>()?;      // Video crossfade (xfade)
    m.add_class::<AcrossfadeBuilder>()?; // Audio crossfade

    // Timeline & clip types
    m.add_class::<ClipInput>()?;
    m.add_class::<ClipWithPosition>()?;
    // ... sanitization functions, etc.
    Ok(())
}
```

**Python API examples:**

```python
from stoat_ferret_core import (
    DrawtextBuilder, SpeedControl, Expr,
    VolumeBuilder, AfadeBuilder, AmixBuilder, DuckingPattern,
    FadeBuilder, XfadeBuilder, AcrossfadeBuilder, TransitionType,
)

# Text overlay with fade
builder = (DrawtextBuilder("Hello World")
    .fontsize(48)
    .fontcolor("white")
    .position("center")
    .alpha_fade(0.0, 1.0, 5.0, 0.5))
filter = builder.build()  # Returns Filter

# Speed control with auto-chained atempo
ctrl = SpeedControl(3.0)          # Validates [0.25, 4.0]
video_filter = ctrl.setpts_filter()    # setpts=0.333333*PTS
audio_filters = ctrl.atempo_filters()  # [atempo=2, atempo=1.5]

# Audio mixing (v007)
mix = AmixBuilder(3).duration_mode("longest").build()  # Returns Filter
vol = VolumeBuilder(0.8).build()                       # volume=0.8
fade = AfadeBuilder("in", 2.0).curve("tri").build()    # afade=t=in:d=2:curve=tri
duck = DuckingPattern().threshold(0.05).build()        # Returns FilterGraph

# Transitions (v007)
vfade = FadeBuilder("in", 1.5).build()                 # fade=t=in:d=1.5
xf = XfadeBuilder(TransitionType.from_str("dissolve"), 1.0, 5.0).build()
acf = AcrossfadeBuilder(1.0).curve1("tri").build()     # acrossfade=d=1:c1=tri

# Expression builder
expr = Expr.between(Expr.var("t"), Expr.constant(2), Expr.constant(5))
str(expr)  # "between(t,2,5)"
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

For long-running operations (directory scanning, rendering) with the async producer-consumer pattern:
- **`asyncio.Queue`-based** in-process job queue with background worker coroutine
- Jobs submitted via API endpoints return immediately with a UUID job ID
- Job status polled via `GET /jobs/{id}` (pending → running → complete/failed/timeout)
- Per-job timeout enforcement via `asyncio.wait_for()` (default 300s)
- Handler registration pattern: `job_queue.register_handler(job_type, handler_fn)`
- **Lifespan integration**: worker started via `asyncio.create_task()` on startup, cancelled on shutdown
- Graceful shutdown cancels worker and suppresses `CancelledError`
- **Test double**: `InMemoryJobQueue` executes synchronously for deterministic testing

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

-- Clips with effects storage
CREATE TABLE clips (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE RESTRICT,
    in_point INTEGER NOT NULL,
    out_point INTEGER NOT NULL,
    timeline_position INTEGER NOT NULL,
    effects_json TEXT,    -- JSON array of {effect_type, parameters, filter_string}
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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

Effects are defined using `EffectDefinition` dataclasses in Python, with each definition including a `preview_fn` for sample output and a `build_fn` that dispatches to the corresponding Rust builder.

```python
@dataclass(frozen=True)
class EffectDefinition:
    name: str                           # Human-readable name
    description: str                    # What the effect does
    parameter_schema: dict[str, object] # JSON Schema for parameters
    ai_hints: dict[str, str]            # Per-parameter AI guidance
    preview_fn: Callable[[], str]       # Calls Rust builder for sample output
    build_fn: Callable[[dict], str]     # Dispatches to Rust builder with user params
```

**Registered effects (v007):**

| Effect Type | Rust Builder | Parameters |
|-------------|-------------|------------|
| `text_overlay` | `DrawtextBuilder` | `text` (required), `fontsize`, `fontcolor`, `position`, `margin`, `font` |
| `speed_control` | `SpeedControl` | `factor` (required, 0.25-4.0), `drop_audio` |
| `audio_mix` | `AmixBuilder` | `inputs` (required, 2-32), `duration_mode`, `weights`, `normalize` |
| `volume` | `VolumeBuilder` | `volume` (required, 0.0-10.0 or dB string), `precision` |
| `audio_fade` | `AfadeBuilder` | `fade_type` (required, "in"/"out"), `duration` (required), `start_time`, `curve` |
| `audio_ducking` | `DuckingPattern` | `threshold`, `ratio`, `attack`, `release` |
| `video_fade` | `FadeBuilder` | `fade_type` (required, "in"/"out"), `duration` (required), `start_time`, `color`, `alpha` |
| `xfade` | `XfadeBuilder` | `transition` (required), `duration` (required, 0-60), `offset` (required) |
| `acrossfade` | `AcrossfadeBuilder` | `duration` (required, 0-60), `curve1`, `curve2`, `overlap` |

**Clip effects storage format** (`effects_json` column):

```json
[
  {
    "effect_type": "text_overlay",
    "parameters": {
      "text": "Chapter 1",
      "fontsize": 64,
      "fontcolor": "white",
      "position": "center"
    },
    "filter_string": "drawtext=text='Chapter 1':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
  }
]
```

The `filter_string` is generated by the Rust builder at application time and stored alongside the parameters for transparency and debugging.

---

## Data Flow

### Video Import Flow (Async)

```
User Request                API Layer            Job Queue             Scan Handler        Storage
     │                          │                     │                      │                 │
     │  POST /videos/scan       │                     │                      │                 │
     │  {path: "/media"}        │                     │                      │                 │
     ├─────────────────────────>│                     │                      │                 │
     │                          │  validate path      │                      │                 │
     │                          │  exists (sync)      │                      │                 │
     │                          │  submit(scan, ...)  │                      │                 │
     │                          ├────────────────────>│                      │                 │
     │                          │  job_id (UUID)      │                      │                 │
     │                          │<────────────────────┤                      │                 │
     │  202 {job_id: "abc..."}  │                     │                      │                 │
     │<─────────────────────────┤                     │                      │                 │
     │                          │                     │                      │                 │
     │                          │              [Background Worker]           │                 │
     │                          │                     │  dequeue job_id      │                 │
     │                          │                     ├─────────────────────>│                 │
     │                          │                     │                      │  scan_directory()│
     │                          │                     │                      │  find video files│
     │                          │                     │                      ├────────────────>│
     │                          │                     │                      │  ffprobe + save │
     │                          │                     │                      │<────────────────┤
     │                          │                     │  result (complete)   │                 │
     │                          │                     │<─────────────────────┤                 │
     │                          │                     │                      │                 │
     │  GET /jobs/{job_id}      │                     │                      │                 │
     ├─────────────────────────>│                     │                      │                 │
     │                          │  get_result(job_id) │                      │                 │
     │                          ├────────────────────>│                      │                 │
     │                          │<────────────────────┤                      │                 │
     │  {status: "complete",    │                     │                      │                 │
     │   result: {scanned: 47}} │                     │                      │                 │
     │<─────────────────────────┤                     │                      │                 │
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
├── gui/                          # Frontend (React/TypeScript/Vite)
│   ├── src/                      # React source code
│   │   ├── main.tsx              # Entry point
│   │   ├── App.tsx               # Root component
│   │   └── assets/               # Static assets
│   ├── dist/                     # Built output (served at /gui)
│   ├── index.html                # HTML template
│   ├── package.json              # Node dependencies
│   ├── vite.config.ts            # Vite build config (proxy to API)
│   ├── tsconfig.json             # TypeScript config
│   └── vitest.config.ts          # Test config
│
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
│   ├── effects/                 # Effects subsystem
│   │   ├── registry.py          # EffectRegistry (register/get/list_all)
│   │   └── definitions.py       # Built-in effect definitions + preview fns
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
│   │       ├── ffmpeg/          # FFmpeg filter/command modules
│   │       │   ├── mod.rs       # Module declarations
│   │       │   ├── filter.rs    # Filter, FilterChain, FilterGraph types
│   │       │   ├── expression.rs # FFmpeg expression tree builder
│   │       │   ├── drawtext.rs  # DrawtextBuilder for text overlays
│   │       │   ├── speed.rs     # SpeedControl (setpts + atempo)
│   │       │   ├── audio.rs     # Audio mixing (VolumeBuilder, AfadeBuilder, AmixBuilder, DuckingPattern)
│   │       │   ├── transitions.rs # Transitions (FadeBuilder, XfadeBuilder, AcrossfadeBuilder)
│   │       │   └── commands.rs  # FFmpeg command construction
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
GET /api/v1/effects
Returns: All registered effects with parameter schemas, AI hints,
         and filter_preview strings generated by Rust builders.
         Powered by EffectRegistry.list_all()

POST /api/v1/projects/{project_id}/clips/{clip_id}/effects
Applies: Effect to clip, generates filter string via Rust builder,
         persists in clip's effects_json column.
         Returns effect_type, parameters, and filter_string.

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
