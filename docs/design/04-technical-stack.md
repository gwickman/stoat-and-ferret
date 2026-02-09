# stoat-and-ferret - Technical Stack

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

This document details the technology selections for the AI-driven video editor using a **hybrid Python/Rust architecture** with a **web-based GUI**. Python provides the API layer for AI discoverability and rapid iteration, Rust delivers high-performance compute cores, and the GUI enables interactive testing and AI Theater Mode viewing.

**Design Rationale:**
- **AI Discoverability**: FastAPI's automatic OpenAPI generation enables AI agents to discover and understand the API
- **Rapid Iteration**: Python enables quick API changes during development
- **Performance**: Rust handles compute-intensive operations with zero-cost abstractions
- **Quality First**: Testing, observability, and operability built in from day one
- **Progressive GUI**: Web interface evolves with API, providing visibility and interaction

---

## Core Stack Summary

### Python Layer

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.11+ | API layer, orchestration |
| API Framework | FastAPI | 0.100+ | REST API with OpenAPI |
| Validation | Pydantic | 2.0+ | Request/response validation |
| Database | SQLite | 3.35+ | Video library metadata |
| Search | SQLite FTS5 | Built-in | Full-text search |
| Job Queue | asyncio.Queue | Built-in | In-process async job processing |

### Rust Core

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Rust | 1.70+ | High-performance core |
| Python Bindings | PyO3 | 0.20+ | Rust-Python FFI |
| Build Tool | maturin | 1.0+ | PyO3 wheel building |
| Property Testing | proptest | 1.0+ | Property-based testing |

### GUI / Frontend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Runtime | Node.js | 18+ | Build tooling |
| Framework | React or Svelte | 18+ / 4+ | UI components |
| Build Tool | Vite | 5+ | Fast HMR, bundling |
| Styling | Tailwind CSS | 3+ | Utility-first CSS |
| State | Zustand or Svelte stores | Latest | Lightweight state management |
| Video Player | HLS.js | 1.4+ | HLS streaming playback |
| HTTP Client | ky or fetch | Latest | API communication |

### External Tools

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Video Processing | FFmpeg | 5.0+ | All video operations |
| Metadata | FFprobe | 5.0+ | Video analysis |
| Preview | libmpv | 0.35+ | Real-time playback |

### Quality Infrastructure

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Structured Logging | structlog | 24.0+ | JSON logs with context |
| Metrics | prometheus-client | 0.17+ | Prometheus metrics export |
| Configuration | pydantic-settings | 2.0+ | Externalized configuration |
| Tracing (optional) | opentelemetry-sdk | 1.20+ | Distributed tracing |
| Python Testing | pytest | 7.4+ | Test framework |
| Python Coverage | pytest-cov | 4.1+ | Coverage measurement |
| Python Async Testing | pytest-asyncio | 0.21+ | Async test support |
| **Black Box Testing** | httpx | 0.25+ | Async HTTP client for API testing |
| **Test Client** | starlette TestClient | Built-in | Synchronous API testing |
| Python Quality | ruff | 0.1+ | Linting + formatting |
| Python Types | mypy | 1.5+ | Static type analysis |
| Rust Quality | clippy | Built-in | Rust linting |
| Rust Formatting | rustfmt | Built-in | Rust formatting |
| GUI Unit Testing | Vitest | 1.0+ | Frontend unit tests |
| GUI E2E Testing | Playwright | 1.40+ | Browser automation |
| GUI Linting | ESLint | 8+ | JavaScript/TypeScript linting |
| GUI Types | TypeScript | 5+ | Static type checking |

### Black Box Testing Infrastructure

The project uses a dedicated black box testing harness (see 07-quality-architecture.md) that validates complete workflows through the REST API. Key design decisions:

| Component | Approach | Rationale |
|-----------|----------|-----------|
| **Rust Core** | Real (not mocked) | Property-tested and pure; mocking would test the wrong thing |
| **FFmpeg** | Recording fake | Captures commands for verification without execution |
| **Storage** | In-memory fake | Fast, isolated per-test |
| **Job Queue** | Synchronous fake | Deterministic for testing |
| **Application Wiring** | `create_app()` DI | Allows injecting test doubles |
| **Fixtures** | Factory pattern | Builder API for test project creation |

---

## Hybrid Architecture Rationale

### Why Python for API Layer

| Benefit | Explanation |
|---------|-------------|
| **AI Discoverability** | FastAPI generates OpenAPI schemas automatically; AI agents can discover and understand the API |
| **Rapid Iteration** | Hot reload, dynamic typing for quick API changes during development |
| **Rich Ecosystem** | Excellent libraries for REST APIs, validation, async I/O, and observability |
| **Developer Ergonomics** | Easy to read, modify, and extend; familiar to most developers |

### Why Rust for Compute Core

| Benefit | Explanation |
|---------|-------------|
| **Zero-Cost Abstractions** | High-level code compiles to optimal machine code |
| **Memory Safety** | No garbage collector, no data races, predictable performance |
| **Compile-Time Guarantees** | Input sanitization verified at compile time, not runtime |
| **CPU Parallelism** | Rayon enables effortless parallel iteration for multi-core utilization |
| **FFI Quality** | PyO3 provides excellent Python bindings with minimal overhead |

### Boundary Between Python and Rust

| Component | Python | Rust |
|-----------|--------|------|
| HTTP handling | Yes | |
| API schema generation | Yes | |
| Effect discovery | Yes | |
| Timeline calculations | | Yes |
| Filter building | | Yes |
| Input sanitization | | Yes |
| FFmpeg command building | | Yes |
| Subprocess execution | Yes | |
| Database operations | Yes | |
| Job queue (asyncio.Queue) | Yes | |
| Metrics/logging | Yes | |

### Why Web-Based GUI

| Benefit | Explanation |
|---------|-------------|
| **Reuses Existing API** | GUI is just another client of the REST API being built |
| **Cross-Platform** | Works on any OS with a modern browser, zero installation |
| **Rapid Iteration** | Vite hot module reload enables instant feedback |
| **Full-Screen Native** | Browser fullscreen API perfect for AI Theater Mode |
| **Progressive Enhancement** | Can evolve from dashboard to full editor incrementally |
| **Deployment Simplicity** | Static files served by same FastAPI server |

### GUI Technology Choices

| Choice | Rationale |
|--------|-----------|
| **React or Svelte** | Component-based, excellent TypeScript support, large ecosystem |
| **Vite** | Fastest HMR, modern ESM-first bundling, great DX |
| **Tailwind CSS** | Utility-first enables rapid UI iteration, no CSS maintenance |
| **Zustand/Svelte stores** | Lightweight state management, no boilerplate |
| **HLS.js** | Native browser HLS support for video streaming |
| **WebSocket** | Real-time updates for activity feed and AI Theater Mode |

---

## Detailed Selections

### Python: API Layer (3.11+)

**Why Python:**
- Excellent subprocess management for FFmpeg
- FastAPI for modern async APIs with OpenAPI
- Rich ecosystem for observability
- Easy AI agent integration
- Rapid development for solo developer

**Why 3.11+:**
- Performance improvements (10-60% faster)
- Better error messages
- Exception groups for complex error handling
- `tomllib` for config files

### FastAPI: REST Framework

**Why FastAPI:**
- Automatic OpenAPI schema generation (critical for AI discovery)
- Native async support for long-running operations
- Pydantic integration for validation
- Built-in dependency injection

```python
# Self-documenting endpoint with Rust integration
@app.post("/effects/text", response_model=EffectResponse)
async def add_text_effect(
    clip_id: str,
    effect: TextOverlayParams,
    rust_core: StoatFerretCore = Depends(get_rust_core),
) -> EffectResponse:
    """Add text overlay with optional fade animation.

    Filter string is generated by Rust core for performance and safety.
    """
    filter_str = rust_core.build_text_overlay_filter(effect.to_rust())
    ...
```

### Rust: Performance Core (1.70+)

**Why Rust:**
- Zero-cost abstractions for compute-intensive operations
- Compile-time memory safety guarantees
- Property-based testing with proptest
- PyO3 provides seamless Python integration

```rust
// Pure functions, fully testable
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> String {
    let sanitized_text = escape_ffmpeg_text(&params.text);
    // ... compile-time safe construction
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn filter_never_panics(text in ".*") {
            let _ = build_text_overlay_filter(&TextOverlayParams { text, .. });
        }
    }
}
```

### PyO3 + maturin: Python-Rust Bridge

**Why PyO3:**
- First-class Rust-Python integration
- Zero-copy where possible
- Type-safe bindings

**Why maturin:**
- Builds PyO3 projects into Python wheels
- Simple development workflow

```bash
# Development
cd rust/stoat_ferret_core
maturin develop  # Build and install to venv

# Production
maturin build --release  # Build wheel
```

---

### Database: SQLite with FTS5

**Why SQLite:**
- Zero configuration (single file)
- Portable (easy backup)
- Sufficient performance for 100K+ videos
- No server process needed

**Why FTS5:**
- Built-in full-text search
- Boolean queries, phrase matching

---

### Video Processing: FFmpeg (Subprocess)

**Why Subprocess (not bindings):**
- Full FFmpeg feature access
- **Transparent command logging** - AI can understand what's happening
- Easier debugging (run commands manually)
- No version compatibility issues

**Why Rust Builds Commands:**
- Type-safe command construction
- Input sanitization at compile time
- Property-based testing ensures valid output

```python
# Python executes commands built by Rust
async def execute(self, command: FFmpegCommand):
    logger.debug("ffmpeg_command", command=command.to_string())
    process = await asyncio.create_subprocess_exec(*command.to_args(), ...)
```

---

### Job Queue: asyncio.Queue

**Why asyncio.Queue:**
- Zero external dependencies (stdlib only)
- Native async/await integration
- In-process producer-consumer pattern
- Background worker via `asyncio.create_task()`
- Timeout enforcement via `asyncio.wait_for()`
- Sufficient for single-instance deployment

---

### GUI: React/Svelte + Vite

**Why React or Svelte:**
- Component-based architecture matches panel-based UI design
- Excellent TypeScript integration
- Large ecosystem of UI libraries
- Both work well with Vite

**Why Vite:**
- Instant server start (no bundling in dev)
- Lightning-fast HMR (<50ms updates)
- Optimized production builds
- First-class TypeScript support

```typescript
// Example: WebSocket hook for real-time updates
import { useEffect, useState } from 'react';

export function useWebSocket(url: string) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [...prev.slice(-99), event]);
    };
    return () => ws.close();
  }, [url]);

  return { events, connected };
}
```

### HLS.js: Video Streaming

**Why HLS.js:**
- Native browser support for HLS streaming
- Adaptive bitrate switching
- Works with FFmpeg-generated HLS segments
- Fallback to native video for Safari

```typescript
// Example: HLS player component
import Hls from 'hls.js';

function VideoPlayer({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (Hls.isSupported() && videoRef.current) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoRef.current);
      return () => hls.destroy();
    }
  }, [src]);

  return <video ref={videoRef} controls />;
}
```

---

## Development Tools

### Package Management: uv

```bash
uv init ai-video-editor
uv add fastapi uvicorn pydantic
uv add --dev pytest ruff mypy maturin
```

### Code Quality

**Python (Ruff):**
```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "UP", "B", "SIM"]
```

**Rust (Clippy):**
```bash
cargo clippy --all-targets -- -D warnings
```

---

## Quality Infrastructure

### Structured Logging: structlog

```python
logger.info(
    "render_started",
    project_id=project_id,
    rust_core_version=rust_core.version(),
)
```

### Metrics: prometheus-client

```python
rust_core_operation_seconds = Histogram(
    "video_editor_rust_core_operation_seconds",
    "Rust core operation duration",
    ["operation"],
)
```

### Health Checks (Includes Rust Core)

```python
@app.get("/health/ready")
async def readiness(rust_core: StoatFerretCore = Depends(get_rust_core)):
    checks = {
        "database": check_database(),
        "ffmpeg": check_ffmpeg(),
        "rust_core": {"status": "ok", "version": rust_core.version()},
    }
    return {"status": "ok", "checks": checks}
```

---

## Dependencies

### Python

```toml
[project]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
    "structlog>=24.1.0",
    "prometheus-client>=0.17.0",
    "pydantic-settings>=2.0.0",
    "websockets>=12.0",  # For WebSocket support
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.25.0",           # Black box API testing
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "maturin>=1.0.0",
]
```

### Rust

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
thiserror = "1.0"

[dev-dependencies]
proptest = "1.0"
```

### GUI (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "hls.js": "^1.4.0",
    "zustand": "^4.4.0",
    "ky": "^1.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vitest": "^1.0.0",
    "@playwright/test": "^1.40.0",
    "eslint": "^8.55.0"
  }
}
```

---

## Deployment

### Development

```bash
# Build Rust core
cd rust/stoat_ferret_core && maturin develop && cd ../..

# Run tests
cargo test --manifest-path rust/Cargo.toml
pytest tests/python/
cd gui && npm test && cd ..

# Start backend (Terminal 1)
uvicorn src.main:app --reload

# Start frontend with hot reload (Terminal 2)
cd gui && npm run dev
```

### Production Build

```bash
# Build GUI for production
cd gui
npm run build  # Output to gui/dist/

# Build Rust wheel
cd rust/stoat_ferret_core
maturin build --release

# GUI served as static files from FastAPI
```

### Production (Container)

```dockerfile
# Stage 1: Build Rust core
FROM rust:1.70 as rust-builder
WORKDIR /build
COPY rust/ ./rust/
RUN pip install maturin
WORKDIR /build/rust/stoat_ferret_core
RUN maturin build --release --out /wheels

# Stage 2: Build GUI
FROM node:20 as gui-builder
WORKDIR /gui
COPY gui/package*.json ./
RUN npm ci
COPY gui/ ./
RUN npm run build

# Stage 3: Production image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Rust wheel
COPY --from=rust-builder /wheels/*.whl /tmp/
RUN pip install /tmp/*.whl

# Install Python application
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install .

# Copy built GUI
COPY --from=gui-builder /gui/dist /app/static/gui

# Non-root user
RUN useradd -m -U appuser
USER appuser

EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health/live || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Version Compatibility

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11 | 3.12 |
| Rust | 1.70 | Latest stable |
| FFmpeg | 5.0 | 6.0+ |
| SQLite | 3.35 | 3.40+ |
| PyO3 | 0.20 | Latest |
| maturin | 1.0 | Latest |
| Node.js | 18 | 20 LTS |
| React | 18 | 18+ |
| Vite | 5 | Latest |
| TypeScript | 5 | Latest |

---

## Performance Targets

| Operation | Target | Component |
|-----------|--------|-----------|
| Filter generation | <1ms | Rust |
| Timeline calculation (100 clips) | <5ms | Rust |
| Path validation | <0.1ms | Rust |
| API response (p95) | <200ms | Python |
| Health check | <100ms | Python |
| GUI initial load | <3s | Frontend |
| GUI interaction response | <100ms | Frontend |
| WebSocket event latency | <50ms | Full stack |
| Theater Mode HUD update | <16ms | Frontend |
| Video preview latency | <200ms | Full stack |
