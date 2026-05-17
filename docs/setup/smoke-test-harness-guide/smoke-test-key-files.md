# Test Harness Key Files

> **Read this file first, then read only the files relevant to your task. Do not read all files listed here unless necessary.**

## What is the Test Harness?

The test harness has three tiers:

1. **Smoke Tests** (`tests/smoke/`) — An API-level integration test suite that runs in-process using `httpx.ASGITransport` (no real HTTP server). It exercises the full application stack including the real Rust core (`stoat_ferret_core`). Tests verify API endpoint contracts, request/response schemas, and end-to-end behaviour from HTTP request through to Rust-level processing.

2. **Contract Tests** (`tests/test_contract/`) — Real FFmpeg execution with synthetic lavfi virtual inputs (LRN-100). Validates encoder output format, codec detection, multi-segment concatenation, and WebSocket event schemas. Covered by the 80% minimum coverage gate. Establishes patterns for future FFmpeg-integration features.

3. **UAT Journeys** (`scripts/uat_journey_*.py`) — Playwright-based Python scripts that drive a real browser against a live server, validating complete user workflows. Each journey captures screenshot evidence and produces structured pass/fail reports. See [`docs/manual/uat-testing.md`](../../manual/uat-testing.md) for full details.

## Key Files

### Phase 1 — Core API Smoke Tests (v014)

| File | What it tells you |
|------|-------------------|
| `tests/smoke/conftest.py` | Shared fixtures, test video setup, ASGITransport client, helpers |
| `tests/smoke/test_scan_workflow.py` | UC-01 and UC-12: video scanning and job cancellation |
| `tests/smoke/test_library.py` | UC-02: library search; also video detail, thumbnail, and delete (v019) |
| `tests/smoke/test_project_workflow.py` | UC-03 and UC-09: project CRUD and deletion |
| `tests/smoke/test_clip_workflow.py` | UC-04 and UC-10: clip add and modify |
| `tests/smoke/test_effects.py` | UC-05, UC-06, UC-11: effects catalog, update/delete, speed and stacking |
| `tests/smoke/test_transitions.py` | UC-07: fade transition |
| `tests/smoke/test_health.py` | UC-08: health live and ready probes; preview and proxy subsystem checks (v026) |

### Phase 2 — Expanded API Smoke Tests (v018–v019)

| File | What it tells you |
|------|-------------------|
| `tests/smoke/test_timeline.py` | Timeline CRUD: create tracks, add/patch/delete clips, transitions (v018) |
| `tests/smoke/test_compose.py` | Composition layout: list presets, apply preset, invalid preset (v018) |
| `tests/smoke/test_audio.py` | Audio mixing: configure mix, preview mix (v018) |
| `tests/smoke/test_batch.py` | Batch operations: submit batch and poll to completion (v018) |
| `tests/smoke/test_versions.py` | Version management: list, restore, not-found, nonexistent project (v019) |
| `tests/smoke/test_filesystem.py` | Filesystem: directory listing, not-found, hidden file exclusion (v019) |
| `tests/smoke/test_negative_paths.py` | Negative paths: invalid inputs across timeline, audio, batch, compose (v019) |
| `tests/smoke/test_proxy.py` | Proxy management: generate, status, delete, batch (v024) |
| `tests/smoke/test_preview.py` | Preview session: create session via POST with timeline, verify 202 and session_id (v026) |
| `tests/smoke/test_render_api.py` | Render API: job CRUD (create, get, list, delete), encoder discovery and refresh, format listing, queue status, cancel, retry (v029–v033). Covers HTTP 404 (`PROJECT_NOT_FOUND`) for non-existent project and HTTP 422 (`EMPTY_TIMELINE` and non-UUID `project_id`) validation error paths for POST /api/v1/render (v065). Verifies `encoder_type` returns bare token values (e.g. `Software`, not `EncoderType.Software`). In noop mode (`STOAT_RENDER_MODE=noop`), the render job's terminal status is authoritative — returns COMPLETED and the background worker does not race noop jobs (v065). |

### Phase 3 — Sample Project Smoke Tests (v034)

| File | What it tells you |
|------|-------------------|
| `tests/smoke/test_sample_project.py` | BL-128/BL-239: full sample project structure (metadata, clips, effects) and render job queueing — asserts `status=="queued"` only (render background worker not wired to lifespan) |

### Conftest Additions (v018–v019)

| Item | Purpose |
|------|---------|
| `create_adjacent_clips_timeline()` | Helper to set up two adjacent clips on a timeline track for transition tests |
| `create_version_repo()` | Factory to create `AsyncSQLiteVersionRepository` from the live ASGI transport DB |

## Contract Test Key Files

### Contract Tests (v033)

| File | What it tells you |
|------|-------------------|
| `tests/test_contract/test_render_contract.py` | Render output format validation (mp4/webm/mov/mkv), encoder detection, multi-segment concat, WebSocket progress schema, and frame streaming endpoint (BL-254, BL-255) |

### Contract Test Patterns

Contract tests use lavfi virtual inputs (LRN-100) to exercise real FFmpeg code paths without requiring pre-recorded media files. Key characteristics:

- `@requires_ffmpeg` guard — skips tests when FFmpeg is not installed
- `@pytest.mark.contract` marker — for selective test execution (`pytest -m contract`)
- Session-scoped fixtures for expensive FFmpeg operations (e.g. `ffmpeg_encoder_output`)
- `lavfi testsrc2` synthetic input — no pre-recorded media files needed
- `ffprobe` validation — verifies output codec name and container format

Example structure from `test_render_contract.py`:

```python
@requires_ffmpeg
@pytest.mark.contract
class TestRenderOutputFormatContract:
    def test_render_format_produces_valid_output(self, tmp_path: Path, ...) -> None:
        """Uses lavfi testsrc2 virtual input to avoid requiring real media files."""
        real = RealFFmpegExecutor()
        result = real.run(["-f", "lavfi", "-i", "testsrc2=duration=1:size=320x240:rate=24", ...])
```

Use this pattern as precedent when adding FFmpeg-integration tests for new encoders or output formats. See LRN-100 for the full established pattern.

## UAT Journey Key Files

### Runner and Journey Scripts

| File | What it tells you |
|------|-------------------|
| `scripts/uat_runner.py` | Orchestrates the full UAT lifecycle: build, server start, seed, journey execution, evidence collection, teardown |
| `scripts/uat_journey_201.py` | J201 — Scan Library: directory scan, video grid, FTS5 search |
| `scripts/uat_journey_202.py` | J202 — Project Clip: project creation, clip management, clips table |
| `scripts/uat_journey_203.py` | J203 — Effects-Timeline: effects apply/edit/remove, timeline canvas, layout presets |
| `scripts/uat_journey_204.py` | J204 — Export-Render: seeds Running Montage, validates clips/effects/timeline |
| `scripts/seed_sample_project.py` | Seeds the Running Montage sample project via API calls for J204 |

### Evidence Output

| Path | What it contains |
|------|-----------------|
| `uat-evidence/` | Base directory for UAT output (gitignored) |
| `uat-evidence/{YYYYMMDD_HHMMSS}/` | Timestamped per-run directory |
| `uat-evidence/{run}/uat-report.json` | Machine-readable structured report |
| `uat-evidence/{run}/uat-report.md` | Human-readable markdown report |
| `uat-evidence/{run}/{journey}/` | Per-journey screenshot directory |

### Reference Documents

| File | What it tells you |
|------|-------------------|
| `docs/setup/smoke-test-harness-guide/03-test-cases.md` | Canonical use case definitions and UAT journey summaries |
| `docs/setup/smoke-test-harness-guide/02-infrastructure.md` | Harness architecture decisions (smoke tests and UAT) |
| `docs/manual/uat-testing.md` | Authoritative UAT manual — how to run, interpret results, troubleshoot |
