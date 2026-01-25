# stoat-and-ferret - Quality Architecture

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

This document defines how quality attributes are built into the video editor from day one, not bolted on later. The **hybrid Python/Rust architecture** leverages each language's strengths for quality:

- **Python (FastAPI)**: Observability, operability, API ergonomics
- **Rust Core**: Testability (pure functions, property testing), security (compile-time guarantees), performance

**Principle:** Quality is not a phase - it's a property of every line of code in both languages.

---

## Quality Attributes Summary

| Attribute | Primary Concern | Python Implementation | Rust Implementation |
|-----------|----------------|----------------------|---------------------|
| **Testability** | Can we verify behavior? | DI, integration tests, fixtures | Pure functions, proptest |
| **Black Box Testing** | Are components wired correctly? | Recording fakes, fixture factories, contract tests | Real core used in all tests |
| **Observability** | Can we see what's happening? | Structured logs, metrics, traces | Timing metrics via Python |
| **Operability** | Can we run it smoothly? | Configuration, health checks | Version reporting |
| **Debuggability** | Can we diagnose problems? | Error context, audit trails | Filter preview, detailed errors |
| **Maintainability** | Can we change it safely? | Modularity, explicit dependencies | Compile-time checks |
| **Deployability** | Can we release safely? | Docker, smoke tests | maturin wheel builds |
| **Reliability** | Does it work consistently? | Retries, recovery | Memory safety, no panics |
| **Security** | Is it protected? | Rate limiting, audit logs | Input sanitization, path validation |

---

## Testability Architecture

### Design Principles

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Hybrid Testability Pyramid                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                           ┌─────────┐                                    │
│                           │   E2E   │  Few, slow, high confidence        │
│                         ┌─┴─────────┴─┐                                  │
│                         │ Integration │  Python + Rust + FFmpeg          │
│                       ┌─┴─────────────┴─┐                                │
│                       │   Rust proptest  │  Property-based, fast         │
│                     ┌─┴─────────────────┴─┐                              │
│                     │  Rust Unit Tests    │  Pure functions, isolated    │
│                   ┌─┴───────────────────────┴─┐                          │
│                   │    Python Unit Tests       │  Service mocks           │
│                 ┌─┴─────────────────────────────┴─┐                      │
│                 │      Static Analysis             │  mypy + clippy       │
│                 └───────────────────────────────────┘                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Rust Core Testability

**Pure Functions with Property Testing:**
```rust
// stoat_ferret_core/src/filters/text_overlay.rs

/// Build FFmpeg drawtext filter string.
/// Pure function - same inputs always produce same outputs.
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> String {
    let sanitized_text = escape_ffmpeg_text(&params.text);
    let (x, y) = params.position.to_coordinates();
    let alpha_expr = build_alpha_expression(
        params.start,
        params.start + params.duration,
        params.fade_in,
        params.fade_out,
    );

    format!(
        "drawtext=text='{}':fontsize={}:fontcolor={}:x={}:y={}:enable='between(t,{},{})':alpha='{}'",
        sanitized_text,
        params.font_size,
        params.font_color,
        x, y,
        params.start,
        params.start + params.duration,
        alpha_expr
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Property: filter never panics for any input
    proptest! {
        #[test]
        fn filter_never_panics(
            text in ".*",
            font_size in 8u32..500,
            start in 0.0f64..1000.0,
            duration in 0.1f64..100.0,
        ) {
            let params = TextOverlayParams {
                text,
                font_size,
                font_color: "white".to_string(),
                position: Position::Center,
                start,
                duration,
                fade_in: 0.0,
                fade_out: 0.0,
            };
            let _ = build_text_overlay_filter(&params);
        }
    }

    // Property: special characters are always escaped
    proptest! {
        #[test]
        fn special_chars_escaped(text in ".*[:'\\\\].*") {
            let sanitized = escape_ffmpeg_text(&text);
            // No unescaped special characters
            assert!(!sanitized.contains(":") || sanitized.contains("\\:"));
            assert!(!sanitized.contains("'") || sanitized.contains("\\'"));
        }
    }

    // Specific test cases
    #[test]
    fn filter_center_position() {
        let params = TextOverlayParams {
            text: "Hello".to_string(),
            font_size: 48,
            font_color: "white".to_string(),
            position: Position::Center,
            start: 0.0,
            duration: 5.0,
            fade_in: 0.0,
            fade_out: 0.0,
        };
        let filter = build_text_overlay_filter(&params);
        assert!(filter.contains("x=(w-text_w)/2"));
        assert!(filter.contains("y=(h-text_h)/2"));
    }
}
```

**Timeline Math as Pure Functions:**
```rust
// stoat_ferret_core/src/timeline/mod.rs

/// Calculate timeline positions for sequential clips.
/// Pure function - no side effects, fully deterministic.
pub fn calculate_timeline_positions(clips: &[ClipInput]) -> Vec<ClipWithPosition> {
    let mut result = Vec::with_capacity(clips.len());
    let mut current_position = 0.0;

    for clip in clips {
        let effective_duration = (clip.out_point - clip.in_point) / clip.speed_factor;
        result.push(ClipWithPosition {
            clip_id: clip.id.clone(),
            timeline_start: current_position,
            timeline_end: current_position + effective_duration,
            effective_duration,
        });
        current_position += effective_duration;
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn timeline_is_contiguous(clips in prop::collection::vec(any::<ClipInput>(), 1..100)) {
            let positioned = calculate_timeline_positions(&clips);

            // Each clip starts where previous ends
            for i in 1..positioned.len() {
                prop_assert!((positioned[i].timeline_start - positioned[i-1].timeline_end).abs() < 0.0001);
            }
        }

        #[test]
        fn total_duration_matches_sum(clips in prop::collection::vec(any::<ClipInput>(), 1..100)) {
            let positioned = calculate_timeline_positions(&clips);

            let expected_total: f64 = clips.iter()
                .map(|c| (c.out_point - c.in_point) / c.speed_factor)
                .sum();

            if let Some(last) = positioned.last() {
                prop_assert!((last.timeline_end - expected_total).abs() < 0.0001);
            }
        }
    }
}
```

### Python Service Testability

**Dependency Injection Pattern:**
```python
# src/services/render.py

class RenderService:
    def __init__(
        self,
        rust_core: StoatFerretCore,   # Rust core via PyO3
        ffmpeg: FFmpegExecutor,        # Subprocess wrapper
        storage: ProjectStorage,
        metrics: MetricsCollector,
        logger: StructuredLogger,
    ):
        self._rust_core = rust_core
        self._ffmpeg = ffmpeg
        self._storage = storage
        self._metrics = metrics
        self._logger = logger

    async def start_render(self, project_id: str, output_path: str) -> RenderJob:
        project = await self._storage.load(project_id)

        # Rust core builds command - tested via proptest
        command = self._rust_core.build_render_command(
            project.to_rust(),
            output_path,
        )

        # Python handles execution and observability
        self._logger.info("render_started", project_id=project_id)
        job = await self._create_job(project_id, command, output_path)
        return job

# Production wiring
def create_render_service(settings: Settings) -> RenderService:
    return RenderService(
        rust_core=StoatFerretCore(),
        ffmpeg=SubprocessFFmpegExecutor(settings.ffmpeg_path),
        storage=FileProjectStorage(settings.project_dir),
        metrics=PrometheusMetrics(),
        logger=StructuredLogger("render"),
    )

# Test wiring - real Rust core, fake everything else
def create_test_render_service() -> RenderService:
    return RenderService(
        rust_core=StoatFerretCore(),     # Use real Rust core
        ffmpeg=FakeFFmpegExecutor(),     # Fake subprocess
        storage=InMemoryProjectStorage(),
        metrics=NullMetrics(),
        logger=NullLogger(),
    )
```

**Protocol for Testable Interfaces:**
```python
# src/protocols.py

from typing import Protocol

class FFmpegExecutor(Protocol):
    async def execute(
        self,
        command: FFmpegCommand,
        on_progress: Callable[[float], None] | None = None,
    ) -> FFmpegResult: ...

    async def probe(self, path: Path) -> ProbeResult: ...

# Real implementation wraps subprocess
class SubprocessFFmpegExecutor:
    async def execute(self, command: FFmpegCommand, ...) -> FFmpegResult:
        # Actually runs ffmpeg subprocess
        ...

# Fake for testing - records commands
class FakeFFmpegExecutor:
    def __init__(self):
        self.executed_commands: list[FFmpegCommand] = []
        self.responses: dict[str, FFmpegResult] = {}

    async def execute(self, command: FFmpegCommand, ...) -> FFmpegResult:
        self.executed_commands.append(command)
        return self.responses.get(command.output_path, FFmpegResult.success())
```

### FFI Boundary Testing

**Type Mapping Tests:**
```python
# tests/integration/test_ffi_boundary.py

import pytest
from stoat_ferret_core import StoatFerretCore, TextOverlayParams

class TestRustPythonBoundary:
    """Verify Python types correctly map to Rust types."""

    def test_text_overlay_params_roundtrip(self):
        """Python params correctly converted to Rust."""
        core = StoatFerretCore()

        params = TextOverlayParams(
            text="Hello: World!",
            font_size=48,
            font_color="white",
            position="center",
            start=0.0,
            duration=5.0,
            fade_in=1.0,
            fade_out=0.5,
        )

        # Call Rust, get filter string back
        filter_str = core.build_text_overlay_filter(params)

        # Verify escaping happened
        assert "Hello\\: World\\!" in filter_str or "Hello\\\\: World\\\\!" in filter_str
        assert "fontsize=48" in filter_str

    def test_rust_error_becomes_python_exception(self):
        """Rust errors are properly converted to Python exceptions."""
        core = StoatFerretCore()

        with pytest.raises(ValueError) as exc_info:
            core.validate_time_range(25.0, 10.0)  # Invalid: in > out

        assert "in_point must be less than out_point" in str(exc_info.value)

    @pytest.mark.parametrize("text", [
        "",
        "Normal text",
        "Special: chars!",
        "Unicode: 日本語",
        "Newlines\nand\ttabs",
        "Quote's and \"doubles\"",
        "Path/like\\text",
    ])
    def test_various_text_inputs(self, text):
        """Various text inputs don't crash Rust."""
        core = StoatFerretCore()
        params = TextOverlayParams(text=text, font_size=48, ...)

        # Should not raise
        filter_str = core.build_text_overlay_filter(params)
        assert isinstance(filter_str, str)
```

**Contract Tests with Real FFmpeg:**
```python
# tests/contract/test_ffmpeg_contract.py

@pytest.mark.contract
class TestFFmpegContractCompliance:
    """Ensure Rust-generated commands are valid FFmpeg syntax."""

    @pytest.fixture
    def test_video(self, tmp_path):
        """Generate real test video."""
        output = tmp_path / "test.mp4"
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=5:size=1920x1080:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
            str(output),
        ], check=True, capture_output=True)
        return output

    @pytest.mark.parametrize("text,position", [
        ("Hello", "center"),
        ("Special 'chars'", "top"),
        ("Unicode: 日本語", "bottom"),
        ("Colon: test", "center"),
    ])
    def test_text_overlay_produces_valid_ffmpeg(
        self,
        text: str,
        position: str,
        test_video: Path,
        tmp_path: Path,
    ):
        """Generated filter should produce valid FFmpeg command."""
        core = StoatFerretCore()
        filter_str = core.build_text_overlay_filter(
            TextOverlayParams(text=text, position=position, font_size=48, start=0, duration=2)
        )

        output = tmp_path / "output.mp4"
        result = subprocess.run(
            ["ffmpeg", "-i", str(test_video), "-vf", filter_str, "-t", "1", str(output)],
            capture_output=True,
        )

        assert result.returncode == 0, f"FFmpeg failed: {result.stderr.decode()}"
```

### Test Infrastructure

**Fixtures:**
```python
# tests/conftest.py

@pytest.fixture
def rust_core():
    """Real Rust core for integration tests."""
    return VideoEditorCore()

@pytest.fixture
def sample_project() -> Project:
    """A project with one video track and two clips."""
    return Project(
        id="test_project",
        name="Test Project",
        output=OutputSettings(width=1920, height=1080, fps=30),
        tracks=[
            Track(
                id="video_main",
                type="video",
                clips=[
                    Clip(id="clip_1", source="/videos/a.mp4", in_point=0, out_point=10),
                    Clip(id="clip_2", source="/videos/b.mp4", in_point=5, out_point=15),
                ],
            )
        ],
    )

@pytest.fixture
def render_service(rust_core):
    """Render service with real Rust core, fake I/O."""
    return RenderService(
        rust_core=rust_core,
        ffmpeg=FakeFFmpegExecutor(),
        storage=InMemoryProjectStorage(),
        metrics=NullMetrics(),
        logger=NullLogger(),
    )
```

---

## Black Box Testing Harness

**Core Principle:** Integration failures—where components work individually but fail when wired together—are the most common and costly defects. The black box testing harness validates complete workflows through the REST API without knowledge of internal implementation.

**Key Design Decision:** Use the **real Rust core** everywhere. It's property-tested and pure. Mock only external systems (FFmpeg, file system, job queue) with recording fakes that capture interactions for verification.

### Harness Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Black Box Testing Harness                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      Test Client Layer                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │    │
│  │  │   HTTP/REST  │  │   WebSocket  │  │   Scenario   │             │    │
│  │  │    Client    │  │    Client    │  │    Runner    │             │    │
│  │  │   (httpx)    │  │ (websockets) │  │   (pytest)   │             │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                            HTTP / WebSocket                                  │
│                                    │                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    Application Under Test                           │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │                     FastAPI Application                       │ │    │
│  │  │  (configured with test wiring via create_app())               │ │    │
│  │  └──────────────────────────────────────────────────────────────┘ │    │
│  │                               │                                    │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │    │
│  │  │ REAL Rust    │ │  Recording   │ │  In-Memory   │              │    │
│  │  │   Core       │ │    FFmpeg    │ │   Storage    │              │    │
│  │  │ (proptest-   │ │   Executor   │ │              │              │    │
│  │  │  verified)   │ │              │ │              │              │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                     Test Infrastructure                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │    │
│  │  │   Fixture    │  │   Assertion  │  │   Contract   │             │    │
│  │  │   Factory    │  │   Library    │  │   Verifier   │             │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recording Test Doubles

Recording fakes capture interactions for verification without executing real external operations.

**Recording FFmpeg Executor:**
```python
# src/testing/fakes.py

class RecordingFFmpegExecutor:
    """Records FFmpeg commands for verification without execution."""

    def __init__(self):
        self.executed_commands: list[FFmpegCommand] = []
        self.probe_calls: list[Path] = []
        self._canned_results: dict[str, FFmpegResult] = {}
        self._canned_probe_results: dict[Path, ProbeResult] = {}

    async def execute(
        self,
        command: FFmpegCommand,
        on_progress: Callable[[float], None] | None = None,
    ) -> FFmpegResult:
        self.executed_commands.append(command)

        # Simulate progress callbacks if handler provided
        if on_progress:
            for pct in [0.25, 0.5, 0.75, 1.0]:
                on_progress(pct)

        return self._canned_results.get(
            command.output_path,
            FFmpegResult.success(output_path=command.output_path)
        )

    async def probe(self, path: Path) -> ProbeResult:
        self.probe_calls.append(path)
        if path in self._canned_probe_results:
            return self._canned_probe_results[path]
        # Default probe result for any path
        return ProbeResult(
            duration=30.0, width=1920, height=1080, fps=30.0, codec="h264"
        )

    # Test configuration helpers
    def set_probe_result(self, path: Path, result: ProbeResult) -> None:
        self._canned_probe_results[path] = result

    def set_render_result(self, output_path: str, result: FFmpegResult) -> None:
        self._canned_results[output_path] = result

    # Verification helpers
    def assert_command_generated(self, containing: str) -> FFmpegCommand:
        """Assert a command was generated containing the given string."""
        for cmd in self.executed_commands:
            if containing in cmd.to_string():
                return cmd
        raise AssertionError(
            f"No command containing '{containing}'. "
            f"Commands: {[c.to_string()[:100] for c in self.executed_commands]}"
        )

    def assert_probe_called(self, path: Path) -> None:
        """Assert FFprobe was called for the given path."""
        assert path in self.probe_calls, f"FFprobe not called for {path}"
```

**In-Memory Storage:**
```python
class InMemoryProjectStorage:
    """Fast, isolated storage for black box tests."""

    def __init__(self):
        self._projects: dict[str, Project] = {}

    async def save(self, project: Project) -> None:
        self._projects[project.id] = deepcopy(project)

    async def load(self, project_id: str) -> Project:
        if project_id not in self._projects:
            raise ProjectNotFoundError(project_id)
        return deepcopy(self._projects[project_id])

    async def delete(self, project_id: str) -> None:
        self._projects.pop(project_id, None)

    async def list_all(self) -> list[ProjectSummary]:
        return [
            ProjectSummary(id=p.id, name=p.name, modified_at=p.modified_at)
            for p in self._projects.values()
        ]

    # Test helpers
    def seed(self, *projects: Project) -> None:
        """Pre-populate storage for test setup."""
        for p in projects:
            self._projects[p.id] = deepcopy(p)

    def get_all(self) -> list[Project]:
        """Retrieve all stored projects for verification."""
        return list(self._projects.values())
```

**Synchronous Job Queue:**
```python
class InMemoryJobQueue:
    """Synchronous job execution for deterministic black box testing."""

    def __init__(self):
        self.jobs: dict[str, RenderJob] = {}
        self._job_results: dict[str, JobResult] = {}

    async def enqueue(self, project_id: str, command: FFmpegCommand) -> RenderJob:
        job_id = f"job_{len(self.jobs) + 1}"
        job = RenderJob(
            id=job_id,
            project_id=project_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.jobs[job_id] = job
        return job

    async def get_status(self, job_id: str) -> RenderJob:
        return self.jobs[job_id]

    async def execute_pending(self, executor: FFmpegExecutor) -> None:
        """Execute all pending jobs synchronously (for test control)."""
        for job in self.jobs.values():
            if job.status == "pending":
                job.status = "running"
                job.status = "completed"
                job.progress = 1.0

    def set_job_result(self, job_id: str, result: JobResult) -> None:
        """Configure outcome for specific job."""
        self._job_results[job_id] = result
```

### Application Test Wiring

```python
# src/api/main.py

def create_app(
    rust_core: StoatFerretCore | None = None,
    ffmpeg: FFmpegExecutor | None = None,
    storage: ProjectStorage | None = None,
    job_queue: JobQueue | None = None,
    metrics: MetricsCollector | None = None,
    logger: StructuredLogger | None = None,
) -> FastAPI:
    """Create application with injectable dependencies.

    Production: called with None (uses real implementations)
    Testing: called with fakes for black box testing
    """
    settings = get_settings()

    app = FastAPI()

    # Use provided dependencies or create production defaults
    app.state.rust_core = rust_core or StoatFerretCore()
    app.state.ffmpeg = ffmpeg or SubprocessFFmpegExecutor(settings.ffmpeg_path)
    app.state.storage = storage or FileProjectStorage(settings.project_dir)
    app.state.job_queue = job_queue or ArqJobQueue(settings.redis_url)
    app.state.metrics = metrics or PrometheusMetrics()
    app.state.logger = logger or StructuredLogger("video_editor")

    # Wire up routes with dependency injection
    configure_routes(app)

    return app

# tests/black_box/conftest.py

@pytest.fixture(scope="session")
def rust_core():
    """Real Rust core - shared across all tests."""
    return StoatFerretCore()

@pytest.fixture
def ffmpeg_recorder():
    """Fresh recording FFmpeg executor per test."""
    return RecordingFFmpegExecutor()

@pytest.fixture
def in_memory_storage():
    """Fresh in-memory storage per test."""
    return InMemoryProjectStorage()

@pytest.fixture
def in_memory_job_queue():
    """Fresh job queue per test."""
    return InMemoryJobQueue()

@pytest.fixture
def test_app(rust_core, ffmpeg_recorder, in_memory_storage, in_memory_job_queue):
    """Application configured for black box testing."""
    app = create_app(
        rust_core=rust_core,           # REAL Rust core
        ffmpeg=ffmpeg_recorder,         # Recording fake
        storage=in_memory_storage,      # In-memory fake
        job_queue=in_memory_job_queue,  # Synchronous fake
        metrics=NullMetrics(),
        logger=NullLogger(),
    )
    return app

@pytest.fixture
def client(test_app):
    """HTTP client for black box testing."""
    return TestClient(test_app)
```

### Fixture Factory Pattern

```python
# src/testing/fixtures.py

class ProjectFixtureFactory:
    """Builder pattern for test project creation."""

    def __init__(self):
        self._name = "Test Project"
        self._clips: list[ClipSpec] = []
        self._effects: list[EffectSpec] = []
        self._output = OutputSettings(width=1920, height=1080, fps=30)

    def with_name(self, name: str) -> "ProjectFixtureFactory":
        self._name = name
        return self

    def with_clip(
        self,
        source: str = "/test/video.mp4",
        in_point: float = 0,
        out_point: float = 10,
    ) -> "ProjectFixtureFactory":
        self._clips.append(ClipSpec(source, in_point, out_point))
        return self

    def with_text_overlay(
        self,
        text: str,
        position: str = "center",
        start: float = 0,
        duration: float = 5,
    ) -> "ProjectFixtureFactory":
        self._effects.append(EffectSpec("text_overlay", {
            "text": text,
            "position": position,
            "start": start,
            "duration": duration,
            "font_size": 48,
        }))
        return self

    def build(self) -> Project:
        """Build the project object (for direct storage seeding)."""
        project = Project(
            id=str(uuid.uuid4()),
            name=self._name,
            output=self._output,
        )
        for clip_spec in self._clips:
            project.add_clip(clip_spec.to_clip())
        for effect_spec in self._effects:
            project.clips[0].add_effect(effect_spec.to_effect())
        return project

    async def create_via_api(self, client: AsyncClient) -> ProjectResult:
        """Create the project through the API (true black box approach)."""
        response = await client.post("/projects", json={
            "name": self._name,
            "output": self._output.dict()
        })
        project_id = response.json()["id"]

        clip_ids = []
        for clip_spec in self._clips:
            clip_response = await client.post(
                f"/projects/{project_id}/clips",
                json=clip_spec.to_request()
            )
            clip_ids.append(clip_response.json()["clip_id"])

        for effect_spec in self._effects:
            await client.post(
                f"/clips/{clip_ids[0]}/effects",
                json=effect_spec.to_request()
            )

        return ProjectResult(id=project_id, clip_ids=clip_ids)


# Usage in tests
def test_render_with_effects(client, project_factory):
    project = (
        project_factory
        .with_name("Integration Test")
        .with_clip("/media/intro.mp4", 0, 30)
        .with_text_overlay("Welcome!", position="center", start=0, duration=5)
        .create_via_api(client)
    )
    # Test using project...
```

### Black Box Test Scenarios

**Core Workflow Integration:**
```python
class TestCoreWorkflowIntegration:
    """Black box tests for complete video editing workflows."""

    def test_scan_discovers_videos_and_extracts_metadata(
        self,
        client: TestClient,
        ffmpeg_recorder: RecordingFFmpegExecutor,
    ):
        """
        Given: A directory with video files exists
        When: Client requests to scan the directory
        Then: Videos are discovered and metadata extracted via FFprobe
        """
        # Arrange: Configure FFprobe responses
        ffmpeg_recorder.set_probe_result(
            Path("/media/video1.mp4"),
            ProbeResult(duration=60.0, width=1920, height=1080, fps=30, codec="h264")
        )

        # Act: Request scan via API
        response = client.post("/videos/scan", json={"path": "/media"})

        # Assert: API response correct
        assert response.status_code == 200

        # Assert: FFprobe was called (black box verification)
        ffmpeg_recorder.assert_probe_called(Path("/media/video1.mp4"))

    def test_add_text_overlay_generates_correct_ffmpeg_filter(
        self,
        client: TestClient,
        ffmpeg_recorder: RecordingFFmpegExecutor,
        project_factory: ProjectFixtureFactory,
    ):
        """
        Given: A project with a video clip exists
        When: Client adds a text overlay effect and renders
        Then: FFmpeg command contains correctly escaped drawtext filter
        """
        # Arrange
        project = project_factory.with_clip().create_via_api(client)

        # Act: Add text overlay with special characters
        client.post(f"/clips/{project.clip_ids[0]}/effects", json={
            "type": "text_overlay",
            "params": {
                "text": "Chapter 1: Introduction",  # Contains colon
                "position": "center",
                "font_size": 48,
                "start": 0,
                "duration": 5,
            }
        })

        # Trigger render
        client.post("/render/start", json={
            "project_id": project.id,
            "output_path": "/output/result.mp4"
        })

        # Assert: FFmpeg command contains escaped text
        cmd = ffmpeg_recorder.assert_command_generated("drawtext")
        assert "Chapter 1\\:" in cmd.to_string()  # Colon properly escaped

    def test_complete_render_workflow(
        self,
        client: TestClient,
        ffmpeg_recorder: RecordingFFmpegExecutor,
        in_memory_job_queue: InMemoryJobQueue,
    ):
        """
        Given: A complete project with clips and effects
        When: Client initiates render
        Then: Job queued, FFmpeg invoked, status updates correctly
        """
        # Arrange
        project_id = setup_complete_project(client)

        # Act: Start render
        response = client.post("/render/start", json={
            "project_id": project_id,
            "output_path": "/output/final.mp4"
        })
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Execute pending jobs (synchronous in test)
        in_memory_job_queue.execute_pending(ffmpeg_recorder)

        # Assert: Status updated to completed
        status = client.get(f"/render/status/{job_id}").json()
        assert status["status"] == "completed"

        # Assert: FFmpeg was invoked with expected structure
        assert len(ffmpeg_recorder.executed_commands) == 1
```

**Error Handling Integration:**
```python
class TestErrorHandlingIntegration:
    """Black box tests for error scenarios."""

    def test_rust_validation_returns_structured_error(self, client):
        """
        Given: A project exists
        When: Client adds effect with invalid parameters
        Then: Structured error returned with Rust validation source
        """
        project_id = create_project_via_api(client)

        response = client.post(f"/clips/clip_1/effects", json={
            "type": "text_overlay",
            "params": {"text": "Title", "font_size": 9999}  # Invalid
        })

        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "RUST_VALIDATION_ERROR"
        assert error["validated_by"] == "rust_core"
        assert "font_size" in error["message"]
```

### Contract Testing for Test Doubles

```python
class TestFakeContractCompliance:
    """Verify test doubles conform to real implementation contracts."""

    @pytest.fixture(params=["real", "fake"])
    def ffmpeg_executor(self, request) -> FFmpegExecutor:
        if request.param == "real":
            pytest.skip("Requires FFmpeg installed")
            return SubprocessFFmpegExecutor()
        return RecordingFFmpegExecutor()

    def test_probe_returns_required_fields(self, ffmpeg_executor, test_video):
        """Both real and fake probe return required ProbeResult fields."""
        result = asyncio.run(ffmpeg_executor.probe(test_video))

        assert hasattr(result, "duration")
        assert hasattr(result, "width")
        assert hasattr(result, "height")
        assert hasattr(result, "fps")
        assert isinstance(result.duration, float)

    def test_execute_returns_ffmpeg_result(self, ffmpeg_executor):
        """Both implementations return proper FFmpegResult."""
        command = FFmpegCommand(
            inputs=["-f", "lavfi", "-i", "testsrc=duration=1"],
            output_path="/dev/null"
        )
        result = asyncio.run(ffmpeg_executor.execute(command))

        assert isinstance(result, FFmpegResult)
        assert hasattr(result, "success")
```

---

## Observability Architecture

### Three Pillars Implementation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Observability Infrastructure                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │   METRICS   │    │    LOGS     │    │   TRACES    │                  │
│  │             │    │             │    │             │                  │
│  │ Prometheus  │    │ Structured  │    │ OpenTelemetry│                 │
│  │ /metrics    │    │ JSON logs   │    │ Correlation │                  │
│  │             │    │             │    │    IDs      │                  │
│  │ Rust timing │    │             │    │             │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                  │                          │
│         └──────────────────┼──────────────────┘                          │
│                            │                                             │
│                   ┌────────┴────────┐                                    │
│                   │  Request Context │                                   │
│                   │  (correlation_id)│                                   │
│                   └─────────────────┘                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Metrics (Including Rust Core)

```python
from prometheus_client import Counter, Histogram, Gauge

# HTTP metrics
http_requests_total = Counter(
    "video_editor_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "video_editor_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Rust core metrics
rust_core_operation_seconds = Histogram(
    "video_editor_rust_core_operation_seconds",
    "Rust core operation duration",
    ["operation"],  # filter_generation, timeline_calculation, path_validation
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)

rust_core_calls_total = Counter(
    "video_editor_rust_core_calls_total",
    "Total calls to Rust core",
    ["operation", "status"],  # status: success, error
)

# Render metrics
render_jobs_total = Counter(
    "video_editor_render_jobs_total",
    "Total render jobs",
    ["status"],
)

render_duration_seconds = Histogram(
    "video_editor_render_duration_seconds",
    "Render job duration",
    ["quality"],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 3600],
)
```

**Timing Rust Operations:**
```python
import time

async def add_effect(clip_id: str, effect: EffectParams) -> Effect:
    # Time the Rust core operation
    start = time.perf_counter()
    try:
        filter_str = rust_core.build_filter(effect.to_rust())
        rust_core_calls_total.labels(operation="filter_generation", status="success").inc()
    except Exception:
        rust_core_calls_total.labels(operation="filter_generation", status="error").inc()
        raise
    finally:
        duration = time.perf_counter() - start
        rust_core_operation_seconds.labels(operation="filter_generation").observe(duration)

    # Continue with Python logic...
```

### Structured Logging

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

async def start_render(project_id: str, output_path: str) -> RenderJob:
    logger.info(
        "render_job_started",
        project_id=project_id,
        output_path=output_path,
        rust_core_version=rust_core.version(),
        correlation_id=get_correlation_id(),
    )

    try:
        # Build command via Rust
        command = rust_core.build_render_command(project, output_path)

        logger.debug(
            "ffmpeg_command_built",
            project_id=project_id,
            filter_count=len(command.filters),
            command_preview=command.to_string()[:200],
        )

        job = await _create_render_job(project_id, command)
        logger.info("render_job_queued", job_id=job.id)
        return job

    except Exception as e:
        logger.error(
            "render_job_failed_to_start",
            project_id=project_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise
```

### Health Checks (Including Rust Core)

```python
@app.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    rust_core: StoatFerretCore = Depends(get_rust_core),
):
    """Can the service handle requests?"""
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}

    # FFmpeg check
    try:
        result = await asyncio.create_subprocess_exec(
            "ffmpeg", "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(result.wait(), timeout=5.0)
        checks["ffmpeg"] = {"status": "ok"}
    except Exception as e:
        checks["ffmpeg"] = {"status": "error", "message": str(e)}

    # Rust core check
    try:
        version = rust_core.version()
        # Quick sanity test
        rust_core.validate_time_range(0.0, 1.0)
        checks["rust_core"] = {"status": "ok", "version": version}
    except Exception as e:
        checks["rust_core"] = {"status": "error", "message": str(e)}

    # Redis check
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "message": str(e)}

    overall_status = "ok" if all(c["status"] == "ok" for c in checks.values()) else "degraded"
    status_code = 200 if overall_status == "ok" else 503

    return JSONResponse(
        content={"status": overall_status, "checks": checks},
        status_code=status_code,
    )
```

---

## Operability Architecture

### Configuration Management

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """All configuration externalized, documented, and validated."""

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/videos.db",
        description="Database connection string",
    )

    # FFmpeg
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to FFmpeg binary")
    ffmpeg_timeout_seconds: int = Field(default=3600, ge=60, le=86400)

    # Storage
    media_roots: list[str] = Field(default=[], description="Allowed directories for media")
    project_dir: str = Field(default="./data/projects")

    # Rust Core
    rust_core_log_timing: bool = Field(
        default=True,
        description="Log timing metrics for Rust core operations",
    )

    # Render limits
    max_concurrent_renders: int = Field(default=1, ge=1, le=10)

    # Observability
    log_level: str = Field(default="INFO")
    metrics_enabled: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_prefix = "VIDEO_EDITOR_"
```

### Graceful Shutdown

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with graceful shutdown."""

    # Startup
    app.state.started_at = datetime.utcnow()
    app.state.shutting_down = False
    app.state.rust_core = StoatFerretCore()

    logger.info(
        "application_starting",
        rust_core_version=app.state.rust_core.version(),
    )

    # Initialize resources
    app.state.db = await create_database()
    app.state.render_queue = await create_render_queue()

    yield

    # Shutdown
    logger.info("application_shutting_down")
    app.state.shutting_down = True

    # Wait for in-progress renders
    await app.state.render_queue.wait_for_completion(timeout=30)

    # Close connections
    await app.state.db.close()

    logger.info("application_stopped")

app = FastAPI(lifespan=lifespan)
```

---

## Debuggability Architecture

### Structured Error Handling

**Errors from Rust Core:**
```python
@dataclass
class StructuredError:
    """Rich error with context for debugging."""

    code: str
    category: str
    message: str
    details: dict | None = None
    suggestion: str | None = None
    correlation_id: str | None = None
    validated_by: str | None = None  # "rust_core" or "python"

    def to_response(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "suggestion": self.suggestion,
                "correlation_id": self.correlation_id,
                "validated_by": self.validated_by,
            }
        }

# Convert Rust errors to structured format
@app.exception_handler(ValueError)
async def rust_value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError from Rust core."""
    error = StructuredError(
        code="RUST_VALIDATION_ERROR",
        category="validation",
        message=str(exc),
        suggestion=_get_suggestion_for_rust_error(str(exc)),
        correlation_id=get_correlation_id(),
        validated_by="rust_core",
    )
    return JSONResponse(status_code=400, content=error.to_response())
```

### Filter Preview for Debugging

```python
@app.post("/effects/preview")
async def preview_effect(
    request: EffectPreviewRequest,
    rust_core: StoatFerretCore = Depends(get_rust_core),
):
    """Preview what filter string would be generated.

    Useful for debugging effects without applying them.
    """
    start = time.perf_counter()

    try:
        filter_str = rust_core.build_filter(request.type, request.params)
        generation_time = time.perf_counter() - start

        return {
            "filter_string": filter_str,
            "params_validated": True,
            "sanitized_params": rust_core.get_sanitized_params(request.params),
            "generation_time_ms": generation_time * 1000,
        }
    except ValueError as e:
        return {
            "filter_string": None,
            "params_validated": False,
            "error": str(e),
        }
```

### Debug Endpoints

```python
@app.get("/debug/status")
async def debug_status(rust_core: StoatFerretCore = Depends(get_rust_core)):
    """Detailed system status for debugging."""
    return {
        "uptime_seconds": (datetime.utcnow() - app.state.started_at).total_seconds(),
        "rust_core": {
            "version": rust_core.version(),
            "healthy": rust_core.self_test(),
        },
        "memory": {
            "rss_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        },
        "ffmpeg_processes": {
            "active": ffmpeg_processes_active._value.get(),
        },
        "render_queue": {
            "pending": len(app.state.render_queue.pending),
            "running": len(app.state.render_queue.running),
        },
    }
```

---

## Maintainability Architecture

### Module Structure (Hybrid)

```
project/
├── src/                      # Python source
│   ├── api/                  # HTTP interface (thin)
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── schemas/          # Pydantic models
│   │
│   ├── services/             # Business logic (orchestration)
│   │   ├── library.py
│   │   ├── timeline.py
│   │   ├── effects.py
│   │   └── render.py
│   │
│   ├── infrastructure/       # External interfaces
│   │   ├── database/
│   │   ├── storage/
│   │   └── queue/
│   │
│   └── observability/        # Cross-cutting
│       ├── logging.py
│       ├── metrics.py
│       └── tracing.py
│
├── rust/                     # Rust source
│   └── stoat_ferret_core/
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs        # PyO3 module definition
│           ├── filters/      # Filter builders (pure)
│           │   ├── mod.rs
│           │   ├── text_overlay.rs
│           │   ├── speed.rs
│           │   └── fade.rs
│           ├── timeline/     # Timeline math (pure)
│           │   └── mod.rs
│           ├── sanitization/ # Input sanitization
│           │   └── mod.rs
│           └── command/      # FFmpeg command builders
│               └── mod.rs
│
└── tests/
    ├── unit/                 # Python unit tests
    ├── integration/          # Python + Rust tests
    └── contract/             # FFmpeg contract tests
```

**Dependency Direction:**
```
                    ┌─────────────────────┐
                    │    API (Python)     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Services (Python)  │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼─────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│ Rust Core (PyO3)  │ │ Infrastructure  │ │   Observability │
│ - Pure functions  │ │ - Database      │ │   - Metrics     │
│ - No side effects │ │ - Storage       │ │   - Logging     │
│ - Compile-time    │ │ - Queue         │ │   - Tracing     │
│   guarantees      │ └─────────────────┘ └─────────────────┘
└───────────────────┘
```

### Explicit Dependencies

```python
# GOOD: Services receive all dependencies explicitly
class RenderService:
    def __init__(
        self,
        rust_core: StoatFerretCore,  # Rust core - explicit
        ffmpeg: FFmpegExecutor,
        storage: ProjectStorage,
        metrics: MetricsCollector,
        logger: StructuredLogger,
    ):
        self._rust_core = rust_core
        self._ffmpeg = ffmpeg
        self._storage = storage
        self._metrics = metrics
        self._logger = logger
```

---

## Deployability Architecture

### Hybrid Build Process

**Multi-stage Docker Build:**
```dockerfile
# Stage 1: Build Rust core
FROM rust:1.70 as rust-builder

WORKDIR /build
COPY rust/stoat_ferret_core/ ./rust/stoat_ferret_core/
RUN cargo build --release --manifest-path rust/stoat_ferret_core/Cargo.toml

# Install maturin and build wheel
RUN pip install maturin
WORKDIR /build/rust/stoat_ferret_core
RUN maturin build --release --out /wheels

# Stage 2: Build Python application
FROM python:3.11-slim as python-builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY src/ src/
RUN uv build

# Stage 3: Production image
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Rust wheel first
COPY --from=rust-builder /wheels/*.whl /tmp/
RUN pip install /tmp/*.whl

# Install Python application
COPY --from=python-builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

# Non-root user
RUN useradd -m -U appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "video_editor.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**CI Pipeline:**
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  rust-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - name: Run Rust tests
        run: cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
      - name: Run Clippy
        run: cargo clippy --manifest-path rust/stoat_ferret_core/Cargo.toml -- -D warnings
      - name: Check formatting
        run: cargo fmt --manifest-path rust/stoat_ferret_core/Cargo.toml -- --check

  python-tests:
    needs: rust-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - name: Install dependencies
        run: |
          pip install maturin
          cd rust/video_editor_core && maturin develop
          pip install -e ".[dev]"
      - name: Run Python tests
        run: pytest tests/unit tests/integration
      - name: Run type checking
        run: mypy src/

  contract-tests:
    needs: python-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - name: Setup Python and Rust
        # ... setup steps ...
      - name: Run contract tests
        run: pytest tests/contract -m contract
```

### Smoke Tests

```python
# tests/smoke/test_smoke.py

BASE_URL = os.environ.get("SMOKE_TEST_URL", "http://localhost:8000")

def test_health_check(client):
    """Service is running and healthy."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    # Rust core must be healthy
    assert data["checks"]["rust_core"]["status"] == "ok"

def test_effects_discoverable(client):
    """Effect discovery endpoint works (uses Rust core)."""
    response = client.get("/effects")
    assert response.status_code == 200
    effects = response.json()["effects"]
    assert len(effects) > 0
    # Verify Rust-generated flag
    assert all(e.get("rust_generated") for e in effects)

def test_filter_preview_works(client):
    """Filter preview endpoint (Rust core) responds."""
    response = client.post("/effects/preview", json={
        "type": "text_overlay",
        "params": {"text": "Test", "position": "center", "font_size": 48, "start": 0, "duration": 5}
    })
    assert response.status_code == 200
    assert "filter_string" in response.json()
```

---

## Reliability Architecture

### Rust Memory Safety

```rust
// Rust guarantees no memory corruption or data races

// All functions return Result for recoverable errors
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> Result<String, FilterError> {
    if params.font_size < 8 || params.font_size > 500 {
        return Err(FilterError::InvalidParameter {
            param: "font_size",
            value: params.font_size.to_string(),
            constraint: "must be between 8 and 500",
        });
    }

    // Safe string building - no buffer overflows
    Ok(format!(...))
}

// PyO3 boundary converts Result to Python exception
#[pyfunction]
fn build_text_overlay(params: TextOverlayParamsRust) -> PyResult<String> {
    build_text_overlay_filter(&params)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}
```

### Python Fault Tolerance

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class FFmpegExecutor:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(FFmpegTransientError),
    )
    async def execute(self, command: FFmpegCommand) -> FFmpegResult:
        # Automatic retry on transient errors
        ...
```

---

## Security Architecture

### Rust-Based Input Sanitization

```rust
// video_editor_core/src/sanitization/mod.rs

/// Escape text for FFmpeg drawtext filter.
/// Prevents command injection through filter parameters.
pub fn escape_ffmpeg_text(text: &str) -> String {
    let mut result = String::with_capacity(text.len() * 2);

    for c in text.chars() {
        match c {
            '\\' => result.push_str("\\\\"),
            '\'' => result.push_str("'\\''"),
            ':' => result.push_str("\\:"),
            '%' => result.push_str("%%"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            _ => result.push(c),
        }
    }

    result
}

/// Validate path is within allowed directories.
pub fn validate_path(path: &Path, allowed_dirs: &[PathBuf]) -> Result<PathBuf, PathError> {
    let canonical = path.canonicalize()
        .map_err(|_| PathError::NotFound)?;

    for allowed in allowed_dirs {
        if canonical.starts_with(allowed) {
            return Ok(canonical);
        }
    }

    Err(PathError::OutsideAllowedDirectory {
        path: path.to_path_buf(),
        allowed: allowed_dirs.to_vec(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn escape_never_produces_unescaped_dangerous_chars(text in ".*") {
            let escaped = escape_ffmpeg_text(&text);
            // After escaping, no unescaped dangerous sequences
            assert!(!escaped.contains("':"));  // Would close quote and start command
        }
    }
}
```

### Python Security Layer

```python
# Rate limiting and audit logging in Python

from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/render/start")
@limiter.limit("10/minute")
async def start_render(request: RenderRequest):
    # Audit log for security events
    await audit.record(
        event_type="render.requested",
        resource_type="project",
        resource_id=request.project_id,
        details={"output_path": request.output_path},
    )
    ...
```

---

## Implementation Phases

### Phase 1 (Foundation) Quality Requirements

**Rust Core:**
- [ ] Pure functions for filter building with proptest coverage
- [ ] Input sanitization module with fuzz testing
- [ ] Timeline calculation with property-based tests
- [ ] PyO3 bindings with error conversion

**Python:**
- [ ] Dependency injection pattern for all services
- [ ] Structured logging with correlation IDs
- [ ] Health check endpoints (including rust_core check)
- [ ] Externalized configuration

**Black Box Testing Harness:**
- [ ] Recording test double catalog (FFmpegExecutor, Storage, JobQueue)
- [ ] Application wiring via `create_app()` with injectable dependencies
- [ ] Fixture factory with builder pattern
- [ ] Contract tests verifying fakes match real implementations
- [ ] Core workflow integration test scenarios
- [ ] pytest fixtures for black box test harness configuration

### Phase 2+ Quality Requirements

Each subsequent phase must maintain and extend quality infrastructure:

- Rust: All new functions must have proptest coverage
- Python: All new code must have >80% test coverage
- All new endpoints must emit metrics
- All new errors must use structured error format
- **Black box tests for each new workflow/feature**
- **Recording fakes updated for new external interactions**

---

## Quality Metrics

### Target SLIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| API availability | 99.9% | Health check success rate |
| API latency (p95) | <500ms | Request duration histogram |
| Rust core latency (p95) | <5ms | Rust operation histogram |
| Render success rate | >95% | Render jobs completed vs failed |
| Error rate | <1% | 5xx responses / total requests |

### Quality Gates for Release

- [ ] All Rust tests passing (including proptest)
- [ ] All Python tests passing
- [ ] Test coverage >80% (Python)
- [ ] No Clippy warnings (Rust)
- [ ] No mypy errors (Python)
- [ ] Smoke tests passing
- [ ] Health checks returning OK (including rust_core)
- [ ] Metrics being collected
- [ ] **Black box integration tests passing**
- [ ] **Contract tests verifying test double compliance**
- [ ] **All core workflows have black box coverage**

---

## Summary

This hybrid quality architecture ensures:

1. **Testability**: Rust proptest for edge cases, Python DI for mocking
2. **Black Box Testing**: Recording fakes capture external interactions; real Rust core always used; fixture factories for test data; contract tests verify fake compliance
3. **Observability**: Python metrics/logs, Rust timing instrumentation
4. **Operability**: Python config/health, Rust version reporting
5. **Debuggability**: Filter preview, structured errors with source
6. **Maintainability**: Compile-time Rust checks, explicit Python dependencies
7. **Deployability**: maturin wheels, multi-stage Docker, comprehensive CI
8. **Reliability**: Rust memory safety, Python retries/recovery
9. **Security**: Rust sanitization (compile-time verified), Python rate limiting

Quality is built into both languages from day one, leveraging each language's strengths.

**Black Box Testing Principle:** The harness validates that components are wired together correctly by testing complete workflows through the REST API. The real Rust core is always used (it's property-tested and pure). Recording fakes capture interactions with external systems (FFmpeg, storage, job queue) for verification without side effects.
