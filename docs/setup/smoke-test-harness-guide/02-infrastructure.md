# Smoke Test Infrastructure Design

## File Layout

```
tests/
  smoke/
    __init__.py
    conftest.py              # Smoke-test-specific fixtures and helpers
    # Phase 1 — Core API (v014)
    test_scan_workflow.py    # UC-1 (scan), UC-12 (cancel scan)
    test_library.py          # UC-2 (search/browse), video detail/thumbnail/delete (v019)
    test_project_workflow.py # UC-3 (create project), UC-9 (delete project)
    test_clip_workflow.py    # UC-4 (add clips), UC-10 (modify clip timing)
    test_effects.py          # UC-5 (apply effect), UC-6 (edit/remove), UC-11 (speed control)
    test_transitions.py      # UC-7 (apply transition)
    test_health.py           # UC-8 (health check)
    # Phase 2 — Expanded API (v018–v019)
    test_timeline.py         # Timeline CRUD, clip position/track changes, transitions
    test_compose.py          # Composition layout presets
    test_audio.py            # Audio mixing configure and preview
    test_batch.py            # Batch operation submit and poll
    test_versions.py         # Version list, restore, error paths
    test_filesystem.py       # Filesystem directory listing
    test_negative_paths.py   # Negative-path validation across domains
```

Naming convention: Phase 1 files use `test_uc<NN>_<short_description>` functions. Phase 2 files use `test_<domain>_<action>` functions.

## conftest.py Design

### EXPECTED_VIDEOS Dictionary

The canonical source of truth for video file metadata used in assertions. Values are from `ffprobe` inspection of the actual files in `/videos/`.

```python
# tests/smoke/conftest.py

import asyncio
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app

VIDEOS_DIR = Path(__file__).parent.parent.parent / "videos"

EXPECTED_VIDEOS = {
    "120449-720880553_medium.mp4": {
        "duration_seconds": 35.84,
        "width": 1280,
        "height": 720,
        "fps_num": 30000,
        "fps_den": 1001,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 1074,
    },
    "15748-266043652_medium.mp4": {
        "duration_seconds": 28.93,
        "width": 1280,
        "height": 720,
        "fps_num": 25,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 723,
    },
    "78888-568004778_medium.mp4": {
        "duration_seconds": 29.73,
        "width": 1280,
        "height": 720,
        "fps_num": 60,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 1784,
    },
    "81872-577880797_medium.mp4": {
        "duration_seconds": 50.99,
        "width": 1280,
        "height": 720,
        "fps_num": 60,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 3059,
    },
    "running1.mp4": {
        "duration_seconds": 29.60,
        "width": 960,
        "height": 540,
        "fps_num": 30,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 888,
    },
    "running2.mp4": {
        "duration_seconds": 22.32,
        "width": 960,
        "height": 540,
        "fps_num": 30000,
        "fps_den": 1001,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 669,
    },
}
```

### `videos_dir` Fixture (session-scoped)

```python
@pytest.fixture(scope="session")
def videos_dir() -> Path:
    """Path to the real /videos/ directory in the repo root."""
    assert VIDEOS_DIR.exists(), f"Videos directory not found: {VIDEOS_DIR}"
    assert len(list(VIDEOS_DIR.glob("*.mp4"))) >= 6, "Expected at least 6 MP4 files"
    return VIDEOS_DIR
```

Session-scoped because the video files are read-only. Every test reads from the same directory.

### `smoke_client` Fixture (per-test)

```python
@pytest.fixture()
async def smoke_client(tmp_path):
    """
    Async httpx client connected to a fresh FastAPI app with an isolated
    temp database. The Rust core is real (not mocked).
    """
    db_path = tmp_path / "smoke_test.db"

    import os
    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")

    app = create_app()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    # Cleanup env vars
    os.environ.pop("STOAT_DATABASE_PATH", None)
    os.environ.pop("STOAT_THUMBNAIL_DIR", None)
```

Key design choices:
- **Per-test scope** — each test gets a fresh database. No shared state between tests.
- **`ASGITransport`** — runs the app in-process. No TCP port binding, no startup delay.
- **`base_url="http://testserver"`** — conventional base URL for in-process ASGI testing.
- **Environment variable overrides** — `STOAT_DATABASE_PATH` and `STOAT_THUMBNAIL_DIR` are the env vars recognized by `Settings` (pydantic-settings with `STOAT_` prefix). This isolates each test's data.
- **Real Rust core** — `create_app()` imports the Rust extension transitively. No mocking.
- **Cleanup** — env vars are removed after the test to prevent leaking into other tests.

### `poll_job_until_terminal()` Helper

```python
async def poll_job_until_terminal(
    client: httpx.AsyncClient,
    job_id: str,
    *,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> dict:
    """
    Poll GET /api/v1/jobs/{job_id} until status is terminal.
    Returns the final job status response body.
    Raises asyncio.TimeoutError if not terminal within timeout.
    """
    terminal_statuses = {"complete", "failed", "timeout", "cancelled"}
    deadline = asyncio.get_event_loop().time() + timeout

    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"].lower() in terminal_statuses:
            return body
        await asyncio.sleep(interval)

    raise asyncio.TimeoutError(
        f"Job {job_id} did not reach terminal status within {timeout}s. "
        f"Last status: {body['status']}"
    )
```

Uses `asyncio.TimeoutError` (not `builtins.TimeoutError`) for Python 3.10 compatibility — these are separate exception classes until Python 3.11.

### `scan_videos_and_wait()` Helper

```python
async def scan_videos_and_wait(
    client: httpx.AsyncClient,
    videos_path: str | Path,
    *,
    timeout: float = 30.0,
) -> dict:
    """
    Submit a scan request and poll until complete.
    Returns the job status response body.
    """
    resp = await client.post(
        "/api/v1/videos/scan",
        json={"path": str(videos_path), "recursive": True},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    return await poll_job_until_terminal(client, job_id, timeout=timeout)
```

### `create_project_with_clips()` Helper

```python
async def create_project_with_clips(
    client: httpx.AsyncClient,
    project_name: str,
    video_ids: list[str],
    clips: list[dict],
) -> tuple[dict, list[dict]]:
    """
    Create a project and add clips to it.
    Returns (project_response, [clip_responses]).

    Each clip dict must contain: source_video_id, in_point, out_point,
    timeline_position (all frame-based integers).
    """
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": project_name},
    )
    assert proj_resp.status_code == 201
    project = proj_resp.json()
    project_id = project["id"]

    clip_responses = []
    for clip in clips:
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json=clip,
        )
        assert clip_resp.status_code == 201
        clip_responses.append(clip_resp.json())

    return project, clip_responses
```

### `sample_project` Fixture (per-test, optional)

```python
@pytest.fixture()
async def sample_project(smoke_client, videos_dir):
    """
    Create the full 'Running Montage' sample project.
    Returns a dict with project, clips, video_ids for complex test scenarios.
    """
    client = smoke_client

    # Scan videos
    await scan_videos_and_wait(client, videos_dir)

    # Resolve video IDs
    resp = await client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    name_to_id = {v["filename"]: v["id"] for v in videos}

    sample_videos = [
        "78888-568004778_medium.mp4",
        "running1.mp4",
        "running2.mp4",
        "81872-577880797_medium.mp4",
    ]
    video_ids = [name_to_id[fn] for fn in sample_videos]

    # Create project at 1280x720 @ 30fps
    resp = await client.post("/api/v1/projects", json={
        "name": "Running Montage",
        "output_width": 1280,
        "output_height": 720,
        "output_fps": 30,
    })
    project = resp.json()
    project_id = project["id"]

    # Add 4 clips (in_point/out_point/timeline_position are integer frames)
    clip_defs = [
        (0, 60, 300, 0),       # Clip 1: establishing shot
        (1, 90, 540, 300),     # Clip 2: running 1
        (2, 30, 360, 750),     # Clip 3: running 2
        (3, 150, 450, 1080),   # Clip 4: outro
    ]
    clip_ids = []
    for vid_idx, in_pt, out_pt, tl_pos in clip_defs:
        resp = await client.post(f"/api/v1/projects/{project_id}/clips", json={
            "source_video_id": video_ids[vid_idx],
            "in_point": in_pt,
            "out_point": out_pt,
            "timeline_position": tl_pos,
        })
        clip_ids.append(resp.json()["id"])

    # Apply effects
    effect_defs = [
        (0, "fade", {"type": "in", "start_time": 0.0, "duration": 1.0}),
        (0, "drawtext", {"text": "Running Montage", "fontsize": 64, "fontcolor": "white"}),
        (1, "speed", {"factor": 0.75}),
        (3, "drawtext", {"text": "The End", "fontsize": 48, "fontcolor": "white"}),
        (3, "fade", {"type": "out", "start_time": 8.0, "duration": 2.0}),
    ]
    for clip_idx, effect_type, params in effect_defs:
        await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_ids[clip_idx]}/effects",
            json={"effect_type": effect_type, "parameters": params},
        )

    # Apply transition between clip 2 and clip 3
    await client.post(f"/api/v1/projects/{project_id}/effects/transition", json={
        "source_clip_id": clip_ids[1],
        "target_clip_id": clip_ids[2],
        "transition_type": "fade",
        "parameters": {"duration": 1.0},
    })

    return {
        "project": project,
        "project_id": project_id,
        "video_ids": video_ids,
        "clip_ids": clip_ids,
    }
```

This fixture is not used by UC-1 through UC-12 (which create their own independent data), but is available for future render/export tests that need a fully-configured project.

### `create_adjacent_clips_timeline()` Helper (v018)

```python
async def create_adjacent_clips_timeline(
    client: httpx.AsyncClient,
    videos_dir: Path,
) -> dict[str, Any]:
    """Create a project with two adjacent clips on the same timeline track.

    Scans videos, creates a project, sets up a timeline with one video track,
    and adds two clips positioned so that clip_a.timeline_end == clip_b.timeline_start.

    Returns:
        Dict with keys: project_id, track_id, clip_a_id, clip_b_id.
    """
```

This helper encapsulates the multi-step setup needed for timeline transition tests (BL-119). It creates a project, scans videos, creates two clips from the same video, sets up a timeline with a video track via `PUT /api/v1/projects/{id}/timeline`, adds both clips to the track at adjacent positions (0.0–5.0 and 5.0–10.0), and verifies adjacency.

### `create_version_repo()` Factory (v019)

```python
def create_version_repo(
    client: httpx.AsyncClient,
) -> AsyncSQLiteVersionRepository:
    """Create an AsyncSQLiteVersionRepository from the live ASGI transport DB.

    Extracts the database connection from the ASGI transport's app.state.db,
    enabling direct version creation in smoke tests (no HTTP endpoint exists
    for creating versions — only listing and restoring).

    Returns:
        An AsyncSQLiteVersionRepository backed by the live test database.
    """
```

This factory is needed because version creation is an internal operation (triggered by timeline changes) with no public HTTP endpoint. Smoke tests for version restore (BL-122) use this to insert version records directly into the database before testing the restore endpoint.

### WebSocket Testing Note

Phase 1 smoke tests use HTTP polling (`poll_job_until_terminal`) rather than WebSocket listeners. WebSocket testing in an ASGI in-process context requires the `httpx-ws` library, which is not currently a project dependency.

If WebSocket assertions are needed in the future, install `httpx-ws` and use its `aconnect_ws` context manager with the ASGI transport. For Phase 1, HTTP polling is simpler, faster, and fully sufficient.

## Rust Core Handling

The Rust core (`stoat_ferret_core`) is **always used as-is** — never mocked. This is consistent with the project's black-box testing philosophy, where Rust provides pure functions that are property-tested in isolation and used as real dependencies in all Python-level tests.

The `maturin develop` build step in CI ensures the compiled Rust extension is available. Smoke tests import `create_app()`, which imports the Rust core transitively through the effects engine and clip validation code. No special handling is needed beyond ensuring CI runs `maturin develop` before the smoke test job.

## Database Isolation Strategy

Each test gets a completely fresh SQLite database:

1. pytest's built-in `tmp_path` fixture creates a unique temporary directory per test
2. A new database file is created at `tmp_path / "smoke_test.db"`
3. The `STOAT_DATABASE_PATH` environment variable is set to point to this file
4. The app's lifespan handler creates the database schema on startup
5. No teardown is needed — pytest cleans up `tmp_path` automatically
6. Environment variables are restored after the test to prevent cross-test leakage

This approach ensures:
- **Full isolation:** Tests cannot interfere with each other
- **No teardown complexity:** No need to truncate tables or drop databases
- **Parallel safety:** If tests are parallelized (e.g., via `pytest-xdist`), each gets its own database

## Environment Variable Handling

The smoke test fixtures override two settings via environment variables:

| Variable | Purpose | Default (from settings.py) |
|----------|---------|---------------------------|
| `STOAT_DATABASE_PATH` | Path to SQLite database file | `data/stoat.db` |
| `STOAT_THUMBNAIL_DIR` | Directory for generated thumbnails | `data/thumbnails` |

Both are set to paths within `tmp_path` for isolation and cleaned up after each test. The `Settings` class (pydantic-settings with `STOAT_` prefix, case-insensitive) reads these automatically.
