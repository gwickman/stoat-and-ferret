# Phase 4: Test Strategy

## Overview

Phase 4 test strategy builds on the established test infrastructure and applies lessons from Phase 1-3 execution. Key principles from learnings: build infrastructure first (LRN-019), pair infrastructure with validation (LRN-073), use production implementations in integration tests (LRN-056), and run smoke tests with `--no-cov` (LRN-075).

## Deferred Items to Resolve First

Two open backlog items should be resolved before or alongside Phase 4 work:

| ID | Item | Rationale for Phase 4 |
|----|------|----------------------|
| BL-086 | Effect preview thumbnail with static frame and applied effect | Preview thumbnails are a Phase 4 concern; thumbnail strip infrastructure enables this. BL-086 tests should verify the frame extraction primitive is shared with the thumbnail strip pipeline. |
| BL-141 | Replace polling-based job progress with WebSocket push events | Preview progress is WebSocket-first; resolve the general pattern before adding preview events. Tests must verify: (a) `JOB_PROGRESS` event broadcast when `set_progress()` called, (b) frontend receives push updates, (c) polling endpoint `GET /api/v1/jobs/{job_id}` still works. |

## Rust Unit Tests

### New Module to Test

**Preview module** (`preview/`):
- `simplify_filter_graph()` - correct simplification at each quality level
- `simplify_filter_chain()` - single chain simplification
- `is_expensive_filter()` - correct classification of filter names
- `estimate_filter_cost()` - bounded cost score (0.0-1.0)
- `inject_preview_scale()` - correct scale filter appended

### Property-Based Tests (proptest)

```rust
proptest! {
    #[test]
    fn simplification_never_panics(
        filter_count in 1usize..20,
        quality in prop::sample::select(vec![
            PreviewQuality::Draft,
            PreviewQuality::Medium,
            PreviewQuality::High,
        ]),
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let _ = simplify_filter_graph(&graph, quality);
    }

    #[test]
    fn simplified_graph_subset_of_original(
        filter_count in 1usize..20,
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let simplified = simplify_filter_graph(&graph, PreviewQuality::Draft);
        assert!(simplified.filter_count() <= graph.filter_count());
    }

    #[test]
    fn cost_estimation_bounded_zero_to_one(
        filter_count in 0usize..20,
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let cost = estimate_filter_cost(&graph);
        assert!(cost >= 0.0);
        assert!(cost <= 1.0);
    }

    #[test]
    fn inject_scale_adds_exactly_one_filter(
        filter_count in 1usize..10,
        max_w in 320u32..3840,
        max_h in 240u32..2160,
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let scaled = inject_preview_scale(&graph, max_w, max_h);
        assert_eq!(scaled.filter_count(), graph.filter_count() + 1);
    }
}
```

### Coverage Target

- New Rust module: >90% line coverage (consistent with existing target)
- Combined Phase 3 + 4 Rust coverage: maintain >95%

## Python Integration Tests

### Recording Fakes (New Test Doubles)

Phase 4 introduces new recording fakes for preview testing:

```python
# tests/test_doubles/preview.py

class RecordingPreviewGenerator:
    """Records preview generation requests without running FFmpeg."""

    def __init__(self):
        self.sessions: list[dict] = []
        self.segments_generated: dict[str, int] = {}

    async def generate_preview(self, session_id: str, project_id: str, **kwargs):
        self.sessions.append({
            "session_id": session_id,
            "project_id": project_id,
            **kwargs,
        })
        # Simulate segment generation
        self.segments_generated[session_id] = kwargs.get("segments_total", 10)
        return {"manifest_path": f"data/previews/{session_id}/manifest.m3u8"}

    def assert_preview_generated(self, project_id: str):
        matching = [s for s in self.sessions if s["project_id"] == project_id]
        assert matching, f"No preview generated for project {project_id}"

    def assert_quality(self, session_id: str, quality: str):
        matching = [s for s in self.sessions if s["session_id"] == session_id]
        assert matching and matching[0].get("quality") == quality


class RecordingProxyGenerator:
    """Records proxy generation requests without running FFmpeg."""

    def __init__(self):
        self.proxies: list[dict] = []

    async def generate_proxy(self, video_id: int, quality: str, **kwargs):
        self.proxies.append({"video_id": video_id, "quality": quality, **kwargs})
        return {"proxy_path": f"data/proxies/{video_id}_{quality}.mp4"}

    def assert_proxy_generated(self, video_id: int, quality: str):
        matching = [p for p in self.proxies
                    if p["video_id"] == video_id and p["quality"] == quality]
        assert matching, f"No proxy generated for video {video_id} at {quality}"


class InMemoryPreviewCache:
    """In-memory preview cache for deterministic testing."""

    def __init__(self, max_bytes: int = 1_073_741_824):
        self.entries: dict[str, dict] = {}
        self.max_bytes = max_bytes

    def add(self, session_id: str, size_bytes: int):
        self.entries[session_id] = {"size_bytes": size_bytes}

    def evict_lru(self) -> str | None:
        if not self.entries:
            return None
        oldest = next(iter(self.entries))
        del self.entries[oldest]
        return oldest

    def usage_percent(self) -> float:
        total = sum(e["size_bytes"] for e in self.entries.values())
        return (total / self.max_bytes) * 100
```

### Black Box Tests (test_blackbox/)

```python
# tests/test_blackbox/test_preview_workflow.py

async def test_full_preview_workflow(client, project_factory, preview_recorder):
    """Black box test: create project with clips -> start preview ->
    check status -> seek -> stop."""
    project = await project_factory.create_with_clips(client, clip_count=3)

    # Start preview
    response = await client.post(
        f"/api/v1/projects/{project.id}/preview/start",
        json={"quality": "720p"}
    )
    assert response.status_code == 202
    session_id = response.json()["session_id"]

    # Check status (recording fake marks it ready immediately)
    response = await client.get(f"/api/v1/preview/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["manifest_url"] is not None

    # Seek
    response = await client.post(
        f"/api/v1/preview/{session_id}/seek",
        json={"position": 10.0}
    )
    assert response.status_code == 200

    # Stop
    response = await client.delete(f"/api/v1/preview/{session_id}")
    assert response.status_code == 200

    # Verify recording fake captured the session
    preview_recorder.assert_preview_generated(project.id)


async def test_preview_empty_timeline_rejected(client, project_factory):
    """Preview start should fail for empty timeline."""
    project = await project_factory.create_via_api(client)  # no clips

    response = await client.post(
        f"/api/v1/projects/{project.id}/preview/start",
        json={}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_TIMELINE"


async def test_proxy_generation_workflow(client, video_factory, proxy_recorder):
    """Black box test: scan video -> generate proxy -> verify status."""
    video_id = await video_factory.create_via_scan(client)

    # Generate proxy
    response = await client.post(
        f"/api/v1/videos/{video_id}/proxy",
        json={"quality": "720p"}
    )
    assert response.status_code == 202

    # Check status
    response = await client.get(f"/api/v1/videos/{video_id}/proxy")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

    proxy_recorder.assert_proxy_generated(video_id, "720p")
```

### New Black Box Test Scenarios

| Scenario | Tests |
|----------|-------|
| Preview lifecycle | Start, status, seek, stop, expired session handling |
| Preview errors | Empty timeline, invalid seek, cache full |
| Proxy CRUD | Generate, status, delete, batch generate, stale detection |
| Thumbnail strips | Generate, retrieve, serve image |
| Waveforms | Generate, retrieve, serve image/data |
| Cache management | Status, eviction, manual clear |
| WebSocket events | preview.ready, preview.generating, proxy.ready |
| Graceful degradation | FFmpeg unavailable, cache full, proxy missing |
| Theater Mode events | ai_action, render_progress via WebSocket |

### Contract Tests (test_contract/)

Contract tests verify FFmpeg commands generated for preview work correctly:

```python
# tests/test_contract/test_preview_contract.py

@pytest.mark.contract
def test_simplified_filter_produces_valid_ffmpeg(test_video):
    """Verify Rust-simplified filter chain works with real FFmpeg."""
    from stoat_ferret_core import (
        simplify_filter_graph, PreviewQuality, inject_preview_scale
    )
    # Build a production filter graph (e.g., text overlay + speed)
    graph = build_test_filter_graph()

    # Simplify for preview
    simplified = simplify_filter_graph(graph, PreviewQuality.Medium)
    scaled = inject_preview_scale(simplified, 1280, 720)

    # Run with real FFmpeg
    result = run_ffmpeg_with_graph(test_video, scaled)
    assert result.returncode == 0


@pytest.mark.contract
def test_hls_segment_generation(test_video, tmp_path):
    """Verify FFmpeg HLS output command produces valid segments."""
    output_dir = tmp_path / "hls"
    output_dir.mkdir()
    manifest = output_dir / "manifest.m3u8"

    result = subprocess.run([
        "ffmpeg", "-i", str(test_video),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-hls_time", "4",
        "-hls_list_size", "0",
        "-hls_segment_filename", str(output_dir / "segment_%03d.ts"),
        str(manifest),
    ], capture_output=True)

    assert result.returncode == 0
    assert manifest.exists()
    assert list(output_dir.glob("segment_*.ts"))


@pytest.mark.contract
def test_thumbnail_strip_generation(test_video, tmp_path):
    """Verify FFmpeg thumbnail strip command produces valid image."""
    strip = tmp_path / "strip.jpg"

    result = subprocess.run([
        "ffmpeg", "-i", str(test_video),
        "-vf", "fps=1/5,scale=160:90,tile=10x1",
        "-frames:v", "1",
        str(strip),
    ], capture_output=True)

    assert result.returncode == 0
    assert strip.exists()
    assert strip.stat().st_size > 0


@pytest.mark.contract
def test_waveform_generation(test_video, tmp_path):
    """Verify FFmpeg waveform command produces valid PNG."""
    waveform = tmp_path / "waveform.png"

    result = subprocess.run([
        "ffmpeg", "-i", str(test_video),
        "-filter_complex", "showwavespic=s=1920x120:colors=white",
        "-frames:v", "1",
        str(waveform),
    ], capture_output=True)

    assert result.returncode == 0
    assert waveform.exists()
```

## Smoke Tests (tests/smoke/)

```python
# tests/smoke/test_preview.py

def test_preview_start(smoke_client, smoke_project_with_clips):
    """Smoke: start preview session for a project."""
    response = smoke_client.post(
        f"/api/v1/projects/{smoke_project_with_clips}/preview/start",
        json={"quality": "720p"}
    )
    assert response.status_code == 202
    assert "session_id" in response.json()


def test_proxy_generate(smoke_client, smoke_video_id):
    """Smoke: generate proxy for a video."""
    response = smoke_client.post(
        f"/api/v1/videos/{smoke_video_id}/proxy",
        json={"quality": "720p"}
    )
    assert response.status_code == 202


def test_preview_cache_status(smoke_client):
    """Smoke: check preview cache status."""
    response = smoke_client.get("/api/v1/preview/cache")
    assert response.status_code == 200
    assert "used_bytes" in response.json()


def test_thumbnail_strip_generate(smoke_client, smoke_video_id):
    """Smoke: generate thumbnail strip."""
    response = smoke_client.post(
        f"/api/v1/videos/{smoke_video_id}/thumbnails/strip",
        json={}
    )
    assert response.status_code == 202


def test_waveform_generate(smoke_client, smoke_video_id):
    """Smoke: generate waveform."""
    response = smoke_client.post(
        f"/api/v1/videos/{smoke_video_id}/waveform",
        json={"format": "png"}
    )
    assert response.status_code == 202
```

## UAT Journeys (Phase 4 Additions)

### J401: Preview Playback

**Goal:** User starts a preview, watches playback, seeks to a position, and verifies the player works.

```
1. Navigate to Projects page
2. Select a project with clips on the timeline
3. Click "Preview" button
4. Wait for preview generation (progress indicator visible)
5. Verify video player appears with controls
6. Click play and verify video plays
7. Click on progress bar at 50% position (seek)
8. Verify video seeks to approximate position
9. Click pause and verify video pauses
10. Verify quality indicator shows current quality
```

### J402: Proxy Management

**Goal:** User scans a library and verifies proxies are generated, then uses them in preview.

```
1. Navigate to Library page
2. Scan a directory with video files
3. Wait for scan to complete
4. Verify proxy status indicators appear on video cards
5. Wait for proxy generation to complete (if auto-generate enabled)
6. Navigate to a project using those videos
7. Start preview and verify it uses proxy quality
```

### J403: AI Theater Mode

**Goal:** User enters Theater Mode, views full-screen playback with HUD, and exits.

```
1. Navigate to Preview page with an active preview
2. Click "Theater Mode" button
3. Verify full-screen mode activates
4. Verify HUD appears with project title and controls
5. Wait 4 seconds and verify HUD auto-hides
6. Move mouse and verify HUD reappears
7. Press Space to pause, verify playback pauses
8. Press Escape to exit Theater Mode
9. Verify return to normal GUI layout
```

### J404: Timeline-Player Synchronization

**Goal:** User verifies that the timeline playhead and preview player stay in sync.

```
1. Open a project with Timeline and Preview visible
2. Start preview playback
3. Verify timeline playhead moves as video plays
4. Click on a position on the timeline
5. Verify video seeks to that position
6. Pause video and verify playhead stops
```

## CI Gate Changes

### New CI Jobs

```yaml
# .github/workflows/ci.yml additions

  rust-preview-tests:
    name: Rust Preview Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo test --manifest-path rust/Cargo.toml -- preview
      - run: cargo test --manifest-path rust/Cargo.toml -- proptest

  preview-smoke:
    name: Preview Smoke Tests
    needs: [rust-tests, python-tests]
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/smoke/test_preview.py --no-cov -v

  preview-contract:
    name: Preview Contract Tests
    needs: [rust-tests]
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/test_contract/test_preview_contract.py -v
```

### Coverage Thresholds

Per LRN-013 (progressive thresholds):
- Rust coverage: maintain >95% after Phase 4 module added
- Python coverage: maintain >80% threshold
- Smoke tests: run with `--no-cov` per LRN-075

## Test Infrastructure Updates

### New Fixtures

```python
# tests/conftest.py additions

@pytest.fixture
def preview_recorder():
    """Recording fake for preview generation."""
    return RecordingPreviewGenerator()

@pytest.fixture
def proxy_recorder():
    """Recording fake for proxy generation."""
    return RecordingProxyGenerator()

@pytest.fixture
def preview_cache():
    """In-memory preview cache for testing."""
    return InMemoryPreviewCache(max_bytes=100_000)

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

Per LRN-076, add grep patterns for Phase 4 changes:

```
# IMPACT_ASSESSMENT.md additions
- Pattern: `PreviewSession|preview_session` -> preview session model changes
- Pattern: `ProxyFile|proxy_file` -> proxy model changes
- Pattern: `PreviewQuality|simplify_filter` -> Rust preview module changes
- Pattern: `ThumbnailStrip|thumbnail_strip` -> thumbnail generation changes
- Pattern: `Waveform|waveform` -> waveform generation changes
- Pattern: `TheaterMode|theater_mode` -> theater mode GUI changes
```
