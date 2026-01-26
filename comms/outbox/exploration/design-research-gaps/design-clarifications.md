# Design Clarifications

## Repository Pattern Scope

### Source: Roadmap M1.4

The exact text from `docs/design/01-roadmap.md` Milestone 1.4:

> ### Milestone 1.4: Database & Storage (Python Layer)
> - [ ] Set up SQLite database with schema for videos, metadata, thumbnails
> - [ ] Implement repository pattern with injectable storage interfaces
> - [ ] Create in-memory storage implementation for testing
> - [ ] Add database migration support with rollback capability
> - [ ] Implement audit logging for data modifications

### Analysis

The roadmap does NOT specify:
- Whether there's one `VideoRepository` or separate repositories
- Whether metadata and thumbnails are separate interfaces
- Specific interface signatures

The quality architecture document (`07-quality-architecture.md`) shows examples using:
- `ProjectStorage` - for project CRUD
- Generic "storage" concept with in-memory fakes

### Recommendation for v002

The roadmap's "injectable storage interfaces" suggests:
- Start with a single `VideoRepository` interface
- Let the interface evolve based on actual usage patterns
- Keep metadata and thumbnails in the same repository initially
- Split later if complexity warrants it

## FFmpeg Executor Boundary

### Design Intent (from multiple sources)

**Roadmap M1.5:**
> - [ ] Create FFmpeg executor protocol for dependency injection
> - [ ] Integrate Rust command builder with Python executor

**Quality Architecture (07-quality-architecture.md):**
```python
class RenderService:
    def __init__(
        self,
        rust_core: StoatFerretCore,   # Rust core via PyO3
        ffmpeg: FFmpegExecutor,        # Subprocess wrapper
        ...
    ):
        ...

    async def start_render(self, project_id: str, output_path: str):
        # Rust core builds command - tested via proptest
        command = self._rust_core.build_render_command(...)

        # Python handles execution and observability
        job = await self._create_job(project_id, command, output_path)
```

**Recording Fake Pattern exploration:**
The `FFmpegExecutor` protocol shows Python handling subprocess execution:
```python
class FFmpegExecutor(Protocol):
    def run(self, args: list[str], ...) -> ExecutionResult: ...
    def probe(self, input_path: str) -> dict: ...
```

### Clear Boundary

| Layer | Responsibility |
|-------|----------------|
| Rust | Build FFmpeg command arguments (`Vec<String>`) |
| Rust | Validate parameters (CRF, paths, codecs) |
| Rust | Escape filter text for safety |
| Python | Execute subprocess with `subprocess.run()` |
| Python | Handle timeouts and retries |
| Python | Parse FFprobe output |
| Python | Emit metrics and logs |
| Python | Progress tracking |

### Why This Design

1. **Testability**: Rust command generation is pure functions, tested with proptest. Python execution uses recording fakes.

2. **Observability**: Python layer emits structured logs, metrics, and traces around subprocess calls.

3. **Safety**: Subprocess execution happens in Python where we have better timeout/signal handling.

4. **Flexibility**: FFmpegExecutor protocol allows swapping real/fake/recording implementations.

## Prometheus Client

### Source: Quality Architecture and Roadmap

**Roadmap M1.1:**
> - [ ] Set up Prometheus metrics collection (/metrics endpoint)

**Dependencies section:**
> ### Quality Infrastructure
> - prometheus-client (metrics)

**Quality Architecture code examples:**
```python
from prometheus_client import Counter, Histogram, Gauge

http_requests_total = Counter(
    "video_editor_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
```

### Library Choice

The design specifies `prometheus-client` - the official Prometheus Python client library.

Package: `prometheus-client` on PyPI
Documentation: https://prometheus.github.io/client_python/

This is the standard choice for Python Prometheus metrics.

## Python Dependencies

### Current State (pyproject.toml)

**Build system:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Runtime dependencies:** NONE currently defined

**Development dependencies only:**
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "maturin>=1.0",
]
```

### Missing Dependencies for v002

Based on roadmap and quality architecture, v002 needs:

**API Layer:**
- `fastapi`
- `uvicorn`
- `pydantic-settings`

**Database:**
- `aiosqlite` (async SQLite)
- `alembic` (migrations)

**Observability:**
- `structlog`
- `prometheus-client`
- `opentelemetry-sdk` (optional tracing)

**Job Queue:**
- `arq` (for background jobs)
- `redis` (or `fakeredis` for testing)

**HTTP Client (for testing):**
- `httpx`

### Recommendation

Add dependencies incrementally as features are implemented. Start with:
1. `fastapi`, `uvicorn` - API layer
2. `pydantic-settings` - Configuration
3. `structlog` - Logging
4. `prometheus-client` - Metrics
