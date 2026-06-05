# Phase 3: Test Strategy

## Overview

Phase 3 test strategy builds on the established test infrastructure (v004) and applies lessons from Phase 1-2 execution. Key principles from learnings: build infrastructure first (LRN-019), pair infrastructure with validation (LRN-073), and use production implementations in integration tests (LRN-056).

## Deferred Phase 2 Quality Items (Resolve First)

Per the plan.md deferred items, these Phase 2 tech debt items should be resolved at the start of Phase 3 before adding composition complexity:

| ID | Item | Rationale for Phase 3 |
|----|------|----------------------|
| BL-081 | Rust filter builder unit test coverage >95% | Coverage becomes critical as Rust core grows |
| BL-082 | Property-based tests (proptest) for filter builders | Batch proptest work with new Phase 3 builders |
| BL-083 | Contract tests with real FFmpeg for Phase 2 builders | Verify all filters work before adding composition |
| BL-084 | Performance benchmarks for Rust filter builders | Baseline before adding composition overhead |

BL-085 (security review) and BL-086 (effect preview thumbnails) are deferred to Phase 6 and Phase 4 respectively per plan.md.

## Rust Unit Tests

### New Modules to Test

**Layout module** (`layout/`):
- `LayoutPosition::to_pixels()` — pixel coordinate math for all edge cases
- `LayoutPosition::validate()` — bounds checking (0.0-1.0 range)
- `LayoutPreset::positions()` — correct positions for each preset/input count
- Aspect ratio preservation calculations

**Compose module** (`compose/`):
- `calculate_composition_positions()` — multi-clip timeline with transitions
- `calculate_timeline_duration()` — duration accounting for overlap
- `build_overlay_filter()` — correct FFmpeg overlay syntax
- `build_scale_for_layout()` — scale filter with aspect ratio
- `build_composition_graph()` — complete FilterGraph for compositions

**AudioMixSpec** (`ffmpeg/audio.rs` extension):
- `build_filter_chain()` — correct amix/volume/afade composition
- `validate()` — volume and fade parameter ranges
- Multi-track coordination with existing builders

**BatchProgress** (`batch.rs`):
- `calculate_batch_progress()` — progress aggregation math

### Property-Based Tests (proptest)

Following LRN-027, proptest catches serialization and edge cases that hand-written tests miss.

```rust
proptest! {
    #[test]
    fn layout_position_always_valid_pixels(
        x in 0.0f64..=1.0,
        y in 0.0f64..=1.0,
        w in 0.01f64..=1.0,
        h in 0.01f64..=1.0,
        out_w in 320u32..3840,
        out_h in 240u32..2160,
    ) {
        let pos = LayoutPosition::new(x, y, w, h, 0);
        let (px, py, pw, ph) = pos.to_pixels(out_w, out_h);
        assert!(px >= 0);
        assert!(py >= 0);
        assert!(pw <= out_w);
        assert!(ph <= out_h);
    }

    #[test]
    fn composition_graph_never_panics(
        clip_count in 1usize..10,
        output_w in 320u32..3840,
        output_h in 240u32..2160,
    ) {
        let clips = generate_test_clips(clip_count);
        let _ = build_composition_graph(clips, vec![], None, None, output_w, output_h);
    }

    #[test]
    fn audio_mix_validates_correctly(
        track_count in 1usize..8,
        volume in 0.0f64..2.0,
    ) {
        let spec = AudioMixSpec::new(track_count);
        assert!(spec.validate().is_ok());
    }
}
```

### Coverage Target

- New Rust modules: >90% line coverage (consistent with existing target)
- Combined Phase 2 + 3 Rust coverage: >95% (resolving BL-081)

## Python Integration Tests

### Black Box Tests (test_blackbox/)

Following the established pattern (LRN-005: constructor DI, LRN-006: builder fixtures):

```python
# tests/test_blackbox/test_composition_workflow.py

async def test_full_composition_workflow(client, project_factory):
    """Black box test: create project → add tracks → add clips → apply
    transition → set layout → configure audio → verify timeline."""
    project = await project_factory.create_via_api(client)

    # Create tracks
    response = await client.put(
        f"/api/v1/projects/{project.id}/timeline",
        json={"tracks": [
            {"id": "v1", "track_type": "video", "label": "Main", "z_index": 0},
            {"id": "a1", "track_type": "audio", "label": "Audio", "z_index": 0},
        ]}
    )
    assert response.status_code == 200

    # Add clips to timeline
    clip1 = await add_clip(client, project.id, "v1", video_id=1, start=0.0)
    clip2 = await add_clip(client, project.id, "v1", video_id=2, start=15.0)

    # Apply transition
    response = await client.post(
        f"/api/v1/projects/{project.id}/timeline/transitions",
        json={
            "source_clip_id": clip1["id"],
            "target_clip_id": clip2["id"],
            "transition_type": "xfade",
            "duration": 1.0,
        }
    )
    assert response.status_code == 201
    assert "filter_string" in response.json()

    # Verify timeline
    timeline = await client.get(f"/api/v1/projects/{project.id}/timeline")
    assert timeline.json()["duration"] > 0
```

### New Black Box Test Scenarios

| Scenario | Tests |
|----------|-------|
| Timeline CRUD | Create tracks, add/move/remove clips, verify positions |
| Transitions | Apply/remove transitions, verify overlap calculation |
| Layout presets | Apply each preset, verify positions generated |
| Custom layout | Custom PIP positioning, out-of-bounds validation |
| Audio mixing | Multi-track volume, fade, normalize |
| Batch render | Submit batch, verify progress tracking |
| Project versioning | Create versions, restore, verify integrity |
| Error handling | Invalid positions, non-adjacent transitions, missing tracks |

### Contract Tests (test_contract/)

Contract tests verify Rust-generated filters work with real FFmpeg:

```python
# tests/test_contract/test_composition_contract.py

@pytest.mark.contract
def test_overlay_filter_valid_ffmpeg(test_video_pair):
    """Verify Rust-generated overlay filter works with real FFmpeg."""
    from stoat_ferret_core import build_overlay_filter, LayoutPosition
    pos = LayoutPosition(0.7, 0.05, 0.25, 0.25, 1)
    filter_str = build_overlay_filter(pos, 1920, 1080, 0.0, 10.0)
    result = run_ffmpeg_with_filter(test_video_pair, filter_str)
    assert result.returncode == 0

@pytest.mark.contract
def test_composition_graph_valid_ffmpeg(test_video_pair):
    """Verify complete composition graph works with real FFmpeg."""
    from stoat_ferret_core import build_composition_graph, CompositionClip
    clips = [CompositionClip(...), CompositionClip(...)]
    graph = build_composition_graph(clips, [], None, None, 1920, 1080)
    result = run_ffmpeg_with_graph(test_video_pair, graph)
    assert result.returncode == 0
```

## Smoke Tests (tests/smoke/)

New smoke test scenarios following the v014 pattern:

```python
# tests/smoke/test_composition.py

def test_timeline_creation(smoke_client, smoke_project):
    """Smoke: create timeline with tracks."""
    response = smoke_client.put(
        f"/api/v1/projects/{smoke_project}/timeline",
        json={"tracks": [{"id": "v1", "track_type": "video", "label": "Main", "z_index": 0}]}
    )
    assert response.status_code == 200

def test_layout_presets(smoke_client):
    """Smoke: list available layout presets."""
    response = smoke_client.get("/api/v1/compose/presets")
    assert response.status_code == 200
    assert len(response.json()["presets"]) > 0

def test_batch_render(smoke_client, smoke_project):
    """Smoke: submit and track batch render."""
    response = smoke_client.post("/api/v1/render/batch", json={
        "jobs": [{"project_id": smoke_project, "output_path": "/tmp/out.mp4"}],
        "parallel": 1,
    })
    assert response.status_code == 202
```

## CI Gate Changes

### New CI Jobs

```yaml
# .github/workflows/ci.yml additions

  rust-composition-tests:
    name: Rust Composition Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo test --manifest-path rust/Cargo.toml -- layout compose batch
      - run: cargo test --manifest-path rust/Cargo.toml -- proptest  # property tests

  composition-smoke:
    name: Composition Smoke Tests
    needs: [rust-tests, python-tests]
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/smoke/test_composition.py --no-cov -v
```

### Coverage Thresholds

Per LRN-013 (progressive thresholds), update after confirming baseline:
- Rust coverage: ratchet from 75% to 85% after Phase 3 core is tested
- Python coverage: maintain >80% threshold
- Smoke tests: run with `--no-cov` per LRN-075

## Test Infrastructure Updates

### New Fixtures

```python
# tests/conftest.py additions

@pytest.fixture
def timeline_factory(project_factory):
    """Factory for creating projects with populated timelines."""
    async def create(client, track_count=1, clip_count=2):
        project = await project_factory.create_via_api(client)
        # Create tracks and clips...
        return project, timeline
    return create

@pytest.fixture
def test_video_pair(test_video):
    """Two test video files for composition tests."""
    return [test_video, test_video]  # or generate second
```

### IMPACT_ASSESSMENT Updates

Per LRN-076, add grep patterns for Phase 3 changes:

```
# IMPACT_ASSESSMENT.md additions
- Pattern: `track_type|TrackType` → composition model changes
- Pattern: `LayoutPosition|LayoutPreset` → layout calculation changes
- Pattern: `AudioMixSpec` → audio mixing changes
- Pattern: `batch_id|BatchProgress` → batch processing changes
```
