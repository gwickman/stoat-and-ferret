# Phase 5: Test Strategy

## Overview

Phase 5 test strategy builds on the established test infrastructure and applies lessons from Phases 1-4 execution. Key principles from learnings: build infrastructure first (LRN-019), pair infrastructure with validation (LRN-073), use production implementations in integration tests (LRN-056), run smoke tests with `--no-cov` (LRN-075), use lavfi virtual inputs for contract tests (LRN-100), and file-based SQLite catches bugs in-memory tests miss (LRN-107).

## Dependencies on Phase 4

Phase 5 render jobs depend on the WebSocket push pattern (BL-141) and the preview subsystem from Phase 4. Test strategy assumes:
- BL-141 (WebSocket push) is implemented and tested
- Preview filter simplification (Phase 4 Rust module) works correctly
- The existing batch render endpoint (Phase 3) has test coverage

If Phase 4 is not yet implemented when Phase 5 begins, the render WebSocket events should use the same pattern as the existing `job.progress` event, with Phase 4's push mechanism as a future enhancement.

## Rust Unit Tests

### New Modules to Test

**Render plan module** (`render/plan.rs`):
- `build_render_plan()` - correct segment count, frame totals, filter graphs
- `validate_render_settings()` - validation catches invalid resolution, fps, empty timeline

**Encoder module** (`render/encoder.rs`):
- `detect_hardware_encoders()` - parses FFmpeg output correctly
- `select_encoder()` - fallback chain works, priority ordering correct
- `build_encoding_args()` - correct CRF/CQ values per preset

**Progress module** (`render/progress.rs`):
- `calculate_progress()` - bounded 0.0-1.0, correct ETA
- `parse_ffmpeg_progress()` - handles various FFmpeg output formats
- `aggregate_segment_progress()` - correct totals across segments

**Command module** (`render/command.rs`):
- `build_render_command()` - correct FFmpeg argument order, input files, filter graph
- `build_concat_command()` - correct concat demuxer format
- `estimate_output_size()` - positive, proportional to duration and bitrate

### Property-Based Tests (proptest)

```rust
proptest! {
    #[test]
    fn progress_always_bounded(
        current in 0u64..100_000,
        total in 1u64..100_000,
        elapsed in 0.0f64..10_000.0,
    ) {
        let progress = calculate_progress(current, total, elapsed);
        prop_assert!(progress.progress >= 0.0);
        prop_assert!(progress.progress <= 1.0);
        prop_assert!(progress.eta_seconds >= 0.0);
    }

    #[test]
    fn render_plan_segments_cover_timeline(
        clip_count in 1usize..10,
        segment_duration in 1.0f64..30.0,
    ) {
        let graph = generate_test_composition_graph(clip_count);
        let settings = default_render_settings();
        let plan = build_render_plan(&graph, &settings, segment_duration);

        // All timeline seconds are covered
        if !plan.segments.is_empty() {
            let first_start = plan.segments[0].start_time;
            let last_end = plan.segments.last().unwrap().end_time;
            prop_assert!(first_start <= 0.001);
            prop_assert!((last_end - plan.total_duration).abs() < 0.1);
        }
    }

    #[test]
    fn encoder_selection_always_returns_encoder(
        format in prop::sample::select(vec![
            OutputFormat::Mp4, OutputFormat::Webm,
            OutputFormat::ProRes, OutputFormat::Mov,
        ]),
    ) {
        let encoders = default_sw_encoders();
        let quality = QualityPreset::High;
        let encoder = select_encoder(&format, &quality, &encoders);
        prop_assert!(encoder.available);
    }

    #[test]
    fn encoding_args_non_empty_for_all_presets(
        quality in prop::sample::select(vec![
            QualityPreset::Draft, QualityPreset::Medium,
            QualityPreset::High, QualityPreset::Lossless,
        ]),
    ) {
        let encoder = sw_h264_encoder();
        let settings = default_render_settings();
        let args = build_encoding_args(&encoder, &quality, &settings);
        prop_assert!(!args.is_empty());
    }

    #[test]
    fn ffmpeg_progress_parse_never_panics(line in ".*") {
        let _ = parse_ffmpeg_progress(&line);
    }
}
```

### Coverage Target

- New Rust render module: >90% line coverage (consistent with existing target)
- Combined Rust coverage: maintain >95%

## Python Integration Tests

### Recording Fakes (New Test Doubles)

Phase 5 introduces recording fakes for render testing:

```python
# tests/test_doubles/render.py

class RecordingRenderExecutor:
    """Records render job executions without running FFmpeg."""

    def __init__(self):
        self.jobs: list[dict] = []
        self.active_jobs: dict[str, dict] = {}

    async def start_render(self, job_id: str, command: list[str], **kwargs):
        self.jobs.append({
            "job_id": job_id,
            "command": command,
            **kwargs,
        })
        self.active_jobs[job_id] = {"status": "rendering", "progress": 0.0}
        # Simulate immediate completion
        self.active_jobs[job_id] = {"status": "completed", "progress": 1.0}
        return {"exit_code": 0, "output_path": kwargs.get("output_path")}

    def assert_render_started(self, job_id: str):
        matching = [j for j in self.jobs if j["job_id"] == job_id]
        assert matching, f"No render started for job {job_id}"

    def assert_encoder_used(self, job_id: str, encoder: str):
        matching = [j for j in self.jobs if j["job_id"] == job_id]
        assert matching
        cmd = " ".join(matching[0]["command"])
        assert encoder in cmd, f"Expected encoder {encoder} in command"


class RecordingHardwareDetector:
    """Returns configured hardware encoder list without running FFmpeg."""

    def __init__(self, encoders: list[dict] | None = None):
        self.encoders = encoders or [
            {"name": "libx264", "type": "software", "available": True, "priority": 100},
            {"name": "libx265", "type": "software", "available": True, "priority": 100},
            {"name": "libvpx-vp9", "type": "software", "available": True, "priority": 100},
            {"name": "prores_ks", "type": "software", "available": True, "priority": 100},
        ]
        self.detection_count = 0

    async def detect(self):
        self.detection_count += 1
        return self.encoders


class InMemoryRenderQueue:
    """In-memory render queue for deterministic testing."""

    def __init__(self, max_concurrent: int = 2, max_depth: int = 20):
        self.queue: list[str] = []
        self.active: list[str] = []
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth

    async def enqueue(self, job_id: str) -> int:
        if len(self.queue) >= self.max_depth:
            raise QueueFullError()
        self.queue.append(job_id)
        return len(self.queue)

    async def dequeue(self) -> str | None:
        if not self.queue or len(self.active) >= self.max_concurrent:
            return None
        job_id = self.queue.pop(0)
        self.active.append(job_id)
        return job_id

    async def complete(self, job_id: str):
        if job_id in self.active:
            self.active.remove(job_id)
```

### Black Box Tests (test_blackbox/)

```python
# tests/test_blackbox/test_render_workflow.py

async def test_full_render_workflow(client, project_factory, render_recorder):
    """Black box test: create project with clips -> start render ->
    check progress -> verify completion."""
    project = await project_factory.create_with_clips(client, clip_count=3)

    # Start render
    response = await client.post(
        f"/api/v1/projects/{project.id}/render",
        json={"output_format": "mp4", "quality_preset": "high"}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Check status (recording fake completes immediately)
    response = await client.get(f"/api/v1/render/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    render_recorder.assert_render_started(job_id)


async def test_render_empty_timeline_rejected(client, project_factory):
    """Render should fail for empty timeline."""
    project = await project_factory.create_via_api(client)  # no clips
    response = await client.post(
        f"/api/v1/projects/{project.id}/render", json={}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_TIMELINE"


async def test_render_cancel(client, project_factory, render_recorder):
    """Black box test: start render -> cancel -> verify cancellation."""
    project = await project_factory.create_with_clips(client, clip_count=3)
    response = await client.post(
        f"/api/v1/projects/{project.id}/render", json={}
    )
    job_id = response.json()["job_id"]

    response = await client.post(f"/api/v1/render/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_render_queue_full(client, project_factory, render_queue):
    """Black box test: fill queue -> verify rejection."""
    project = await project_factory.create_with_clips(client, clip_count=1)
    # Fill queue to max
    for _ in range(render_queue.max_depth):
        await client.post(f"/api/v1/projects/{project.id}/render", json={})

    # Next should be rejected
    response = await client.post(f"/api/v1/projects/{project.id}/render", json={})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RENDER_QUEUE_FULL"


async def test_render_retry_failed_job(client, project_factory, render_recorder):
    """Black box test: failed render -> retry -> verify requeue."""
    # Setup: create a job that will fail
    # ... simulate failure via recording fake ...
    response = await client.post(f"/api/v1/render/{job_id}/retry")
    assert response.status_code == 202
    assert response.json()["retry_count"] == 1
```

### New Black Box Test Scenarios

| Scenario | Tests |
|----------|-------|
| Render lifecycle | Start, progress, completion, output file verification |
| Render errors | Empty timeline, invalid settings, disk space, queue full |
| Render cancellation | Cancel active job, cancel pending job, cancel completed (409) |
| Render retry | Retry failed job, retry non-failed (409), retry exhaustion |
| Render queue | Queue ordering, concurrent limit, queue depth limit |
| Hardware encoders | Detection, fallback chain, encoder selection |
| Output formats | All format/preset combinations, two-pass encoding |
| WebSocket events | render.started, render.progress, render.completed, render.failed |
| Crash recovery | Checkpoint creation, job recovery on restart |
| Job management | List with filters, delete completed, clean old jobs |

### Contract Tests (test_contract/)

Contract tests verify FFmpeg commands generated for render work correctly:

```python
# tests/test_contract/test_render_contract.py

@pytest.mark.contract
def test_render_plan_produces_valid_ffmpeg(test_video, tmp_path):
    """Verify Rust render plan generates working FFmpeg commands."""
    from stoat_ferret_core import (
        build_render_plan, RenderSettings, OutputFormat, QualityPreset,
        build_encoding_args, select_encoder, build_render_command,
    )

    # Build render plan from test composition
    graph = build_test_composition_graph(test_video)
    settings = RenderSettings(
        format=OutputFormat.Mp4,
        quality=QualityPreset.Draft,
        width=640, height=480, fps=30.0,
        video_bitrate=1_000_000,
        audio_bitrate=128_000,
        two_pass=False,
    )
    plan = build_render_plan(graph, settings, 0.0)

    # Select encoder and build command
    encoders = [{"name": "libx264", "type": "software", "available": True, "priority": 100}]
    encoder = select_encoder(settings.format, settings.quality, encoders)
    enc_args = build_encoding_args(encoder, settings.quality, settings)

    output_path = str(tmp_path / "output.mp4")
    command = build_render_command(plan.segments[0], enc_args, ["-c:a", "aac"], output_path, None)

    # Run with real FFmpeg using lavfi virtual input (LRN-100)
    result = subprocess.run(command, capture_output=True, timeout=30)
    assert result.returncode == 0
    assert Path(output_path).exists()
    assert Path(output_path).stat().st_size > 0


@pytest.mark.contract
def test_hw_encoder_detection_parses_ffmpeg_output():
    """Verify hardware detection parses real FFmpeg encoder list."""
    from stoat_ferret_core import detect_hardware_encoders

    encoders = detect_hardware_encoders("ffmpeg")
    # At minimum, software encoders should be detected
    sw_names = [e.name for e in encoders if e.encoder_type == "software"]
    assert "libx264" in sw_names


@pytest.mark.contract
def test_concat_produces_valid_output(test_video, tmp_path):
    """Verify concat demuxer joins segments correctly."""
    from stoat_ferret_core import build_concat_command

    # Create two short segments
    seg1 = tmp_path / "seg1.mp4"
    seg2 = tmp_path / "seg2.mp4"
    # ... generate segments with FFmpeg ...

    output = tmp_path / "concat_output.mp4"
    command = build_concat_command([str(seg1), str(seg2)], str(output))

    result = subprocess.run(command, capture_output=True, timeout=30)
    assert result.returncode == 0
    assert output.exists()


@pytest.mark.contract
@pytest.mark.parametrize("format_name,extension", [
    ("mp4", ".mp4"),
    ("webm", ".webm"),
    ("prores", ".mov"),
    ("mov", ".mov"),
])
def test_output_format_produces_valid_file(test_video, tmp_path, format_name, extension):
    """Verify each output format produces a valid file."""
    # Build and run render for each format
    output = tmp_path / f"output{extension}"
    # ... build command and run FFmpeg ...
    assert output.exists()
    assert output.stat().st_size > 0
```

## Smoke Tests (tests/smoke/)

```python
# tests/smoke/test_render.py

def test_render_start(smoke_client, smoke_project_with_clips):
    """Smoke: start render job for a project."""
    response = smoke_client.post(
        f"/api/v1/projects/{smoke_project_with_clips}/render",
        json={"output_format": "mp4", "quality_preset": "draft"}
    )
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_render_queue_status(smoke_client):
    """Smoke: check render queue status."""
    response = smoke_client.get("/api/v1/render/queue")
    assert response.status_code == 200
    assert "active_renders" in response.json()


def test_render_encoders(smoke_client):
    """Smoke: list available encoders."""
    response = smoke_client.get("/api/v1/render/encoders")
    assert response.status_code == 200
    assert "encoders" in response.json()
    assert len(response.json()["encoders"]) > 0


def test_render_formats(smoke_client):
    """Smoke: list available output formats."""
    response = smoke_client.get("/api/v1/render/formats")
    assert response.status_code == 200
    formats = response.json()["formats"]
    assert any(f["id"] == "mp4" for f in formats)


def test_render_list(smoke_client):
    """Smoke: list render jobs."""
    response = smoke_client.get("/api/v1/render")
    assert response.status_code == 200
    assert "jobs" in response.json()
```

## UAT Journeys (Phase 5 Additions)

### J501: Export Video

**Goal:** User renders a project to MP4 and monitors progress.

```
1. Navigate to Projects page
2. Select a project with clips on the timeline
3. Click "Start Render" (or navigate to Render page)
4. Verify Start Render modal appears
5. Select MP4 format and High quality
6. Verify disk space check shows green
7. Click "Start Render"
8. Verify job appears in Active Renders list
9. Verify progress bar updates
10. Wait for completion
11. Verify completed job appears in History with file size
```

### J502: Render Queue Management

**Goal:** User queues multiple renders and manages the queue.

```
1. Navigate to Render page
2. Start render for Project A
3. Start render for Project B
4. Verify queue shows 2 jobs (1 active, 1 pending if max_concurrent=1)
5. Cancel the pending job
6. Verify cancelled job moves to History
7. Wait for active job to complete
8. Verify queue shows 0 active, 0 pending
```

### J503: Render Settings and Formats

**Goal:** User explores output formats and encoder options.

```
1. Navigate to Render page
2. Click "Start Render"
3. Select different output formats (MP4, WebM, ProRes)
4. Verify quality presets change per format
5. Verify encoder selector shows available encoders
6. Verify disk space estimate updates with settings changes
7. Verify FFmpeg command preview updates
8. Cancel without starting
```

### J504: Failed Render Recovery

**Goal:** User handles a failed render and retries.

```
1. Navigate to Render page
2. (Setup: trigger a render failure via test conditions)
3. Verify failed job appears in History with error message
4. Click "Retry" on the failed job
5. Verify job requeues with incremented retry count
6. Verify retry eventually succeeds or exhausts retries
```

## CI Gate Changes

### New CI Jobs

```yaml
# .github/workflows/ci.yml additions

  rust-render-tests:
    name: Rust Render Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo test --manifest-path rust/Cargo.toml -- render
      - run: cargo test --manifest-path rust/Cargo.toml -- proptest

  render-smoke:
    name: Render Smoke Tests
    needs: [rust-tests, python-tests]
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/smoke/test_render.py --no-cov -v

  render-contract:
    name: Render Contract Tests
    needs: [rust-tests]
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/test_contract/test_render_contract.py -v
```

### Coverage Thresholds

Per LRN-013 (progressive thresholds):
- Rust coverage: maintain >95% after Phase 5 module added
- Python coverage: maintain >80% threshold
- Smoke tests: run with `--no-cov` per LRN-075

## Test Infrastructure Updates

### New Fixtures

```python
# tests/conftest.py additions

@pytest.fixture
def render_recorder():
    """Recording fake for render execution."""
    return RecordingRenderExecutor()

@pytest.fixture
def hw_detector():
    """Recording fake for hardware detection."""
    return RecordingHardwareDetector()

@pytest.fixture
def render_queue():
    """In-memory render queue for testing."""
    return InMemoryRenderQueue(max_concurrent=2, max_depth=5)

@pytest.fixture
def project_with_clips(project_factory, client):
    """Factory for projects that have clips on the timeline."""
    async def create(clip_count=3):
        project = await project_factory.create_via_api(client)
        # Add tracks and clips...
        return project
    return create
```

### IMPACT_ASSESSMENT Updates

Per LRN-076, add grep patterns for Phase 5 changes:

```
# IMPACT_ASSESSMENT.md additions
- Pattern: `RenderJob|render_job` -> render job model changes
- Pattern: `RenderPlan|render_plan|build_render_plan` -> Rust render plan changes
- Pattern: `HardwareEncoder|hardware_encoder|detect_hardware` -> encoder detection changes
- Pattern: `RenderProgress|render_progress|calculate_progress` -> progress tracking changes
- Pattern: `RenderQueue|render_queue` -> render queue changes
- Pattern: `OutputFormat|QualityPreset` -> output format/preset changes
- Pattern: `RenderCheckpoint|render_checkpoint` -> crash recovery changes
```
