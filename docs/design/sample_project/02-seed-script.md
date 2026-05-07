# Seed Script Design

## Script: `scripts/seed_sample_project.py`

A standalone Python script that creates the "Running Montage" sample project by making HTTP requests to a running stoat-and-ferret instance.

## Usage

```bash
# Basic usage — seed against local server
python scripts/seed_sample_project.py http://localhost:8765

# Specify a custom videos directory
python scripts/seed_sample_project.py http://localhost:8765 --videos-dir ./videos

# Force recreate if the sample project already exists
python scripts/seed_sample_project.py http://localhost:8765 --force
```

## Argument Parsing: `parse_args()`

```python
import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the 'Running Montage' sample project"
    )
    parser.add_argument(
        "base_url",
        help="Base URL of the running stoat-and-ferret instance (e.g., http://localhost:8765)",
    )
    parser.add_argument(
        "--videos-dir",
        default="videos",
        help="Path to directory containing the video files (default: ./videos)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing sample project and recreate",
    )
    return parser.parse_args()
```

## Module-Level Constants

These constants define the exact project structure and must match the project definition in `docs/design/sample_project/01-project-definition.md`.

```python
PROJECT_NAME = "Running Montage"

# Ordered list of the 4 videos used (subset of 6 in /videos/)
SAMPLE_VIDEOS = [
    "78888-568004778_medium.mp4",
    "running1.mp4",
    "running2.mp4",
    "81872-577880797_medium.mp4",
]

# Clip definitions: (video_index, in_point_frames, out_point_frames, timeline_position_frames)
# All values are integer frame counts at the 30fps project output rate
CLIP_DEFS = [
    (0, 60, 300, 0),       # Clip 1: establishing shot, 2s-10s
    (1, 90, 540, 300),     # Clip 2: running 1, 3s-18s
    (2, 30, 360, 750),     # Clip 3: running 2, 1s-12s
    (3, 150, 450, 1080),   # Clip 4: outro, 5s-15s
]

# Effects: (clip_index, effect_type, parameters)
# Uses registered API effect names, not FFmpeg filter names
EFFECT_DEFS = [
    (0, "video_fade", {"fade_type": "in", "start_time": 0.0, "duration": 1.0}),
    (0, "text_overlay", {"text": "Running Montage", "fontsize": 64, "fontcolor": "white"}),
    (1, "speed_control", {"factor": 0.75}),
    (3, "text_overlay", {"text": "The End", "fontsize": 48, "fontcolor": "white"}),
    (3, "video_fade", {"fade_type": "out", "start_time": 8.0, "duration": 2.0}),
]

# Transitions: (source_clip_index, target_clip_index, transition_type, parameters)
TRANSITION_DEFS = [
    (1, 2, "xfade", {"transition": "fade", "duration": 1.0, "offset": 0.0}),
]

# Required top-level fields in render_plan JSON (mirrors worker.py contract)
_REQUIRED_PLAN_FIELDS = ("settings", "total_duration")
```

## `SeedResult` Dataclass

```python
from dataclasses import dataclass

@dataclass
class SeedResult:
    project_id: str
    video_ids: list[str]
    clip_ids: list[str]
    effects_applied: int
    transitions_applied: int
    job_id: str
```

## render_plan Structure

The seed script queues a render job as the final step of project creation. The `render_plan` field is a
JSON-encoded string passed to `POST /api/v1/render`. It must contain two top-level keys:

```json
{
  "settings": {
    "quality_preset": "standard"
  },
  "total_duration": 46.0
}
```

**Valid `quality_preset` values** (public application vocabulary):

| Value | CRF | Description |
|-------|-----|-------------|
| `draft` | 28 | Fast preview quality — smaller file, lower fidelity |
| `standard` | 23 | Balanced quality/size — default for most workflows |
| `high` | 18 | High fidelity — larger file, best quality |

CRF values apply to x264/x265 encoding. The worker maps each preset to its CRF value internally.

**Passing `render_plan` to the API:**

The field is serialized as a JSON string, not a nested object:

```python
import json

render_plan = {
    "settings": {"quality_preset": "standard"},
    "total_duration": total_duration,
}
resp = client.post(
    "/api/v1/render",
    json={"project_id": project_id, "render_plan": json.dumps(render_plan)},
)
```

**Do not use FFmpeg speed preset names** (`veryfast`, `medium`, `slow`) in `quality_preset`. These are
internal FFmpeg presets mapped by the worker — they are not part of the public API vocabulary.

## Function Signatures and Designs

### `find_existing_project(client) → str | None`

Searches the project list for a project with the name "Running Montage". Returns the project ID if found, `None` otherwise.

```python
def find_existing_project(client: httpx.Client) -> str | None:
    resp = client.get("/api/v1/projects", params={"limit": 100})
    resp.raise_for_status()
    for proj in resp.json()["projects"]:
        if proj["name"] == PROJECT_NAME:
            return str(proj["id"])
    return None
```

### `delete_project(client, project_id)`

Deletes an existing project. Used when `--force` is specified.

```python
def delete_project(client: httpx.Client, project_id: str) -> None:
    resp = client.delete(f"/api/v1/projects/{project_id}")
    resp.raise_for_status()
```

### `scan_and_wait(client, videos_dir)`

Submits a scan request and polls until the job reaches a terminal status. Uses synchronous polling with `time.sleep()` (the seed script is synchronous, unlike the async smoke tests).

```python
def scan_and_wait(client: httpx.Client, videos_dir: str) -> None:
    resp = client.post(
        "/api/v1/videos/scan",
        json={"path": videos_dir, "recursive": True},
    )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]

    import time
    for _ in range(120):  # 60 seconds max (120 * 0.5s)
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        status_resp.raise_for_status()
        status = status_resp.json()["status"].lower()
        if status in ("complete", "failed", "timeout", "cancelled"):
            if status != "complete":
                print(f"ERROR: Scan failed with status: {status}", file=sys.stderr)
                sys.exit(1)
            return
        time.sleep(0.5)

    print("ERROR: Scan timed out after 60 seconds", file=sys.stderr)
    sys.exit(1)
```

### `videos_already_scanned(client, filenames) → bool`

Checks whether all expected video filenames are already present in the library. Used in `main()` to skip the scan step when videos were previously scanned (e.g. on re-seed without `--force`).

```python
def videos_already_scanned(client: httpx.Client, filenames: list[str]) -> bool:
    resp = client.get("/api/v1/videos", params={"limit": 100})
    resp.raise_for_status()
    existing = {v["filename"] for v in resp.json()["videos"]}
    return all(fn in existing for fn in filenames)
```

### `resolve_video_ids(client, filenames) → list[str]`

Maps the 4 sample video filenames to their database IDs. Exits with a clear error if any video is missing (indicating the scan didn't find the expected files).

```python
def resolve_video_ids(client: httpx.Client, filenames: list[str]) -> list[str]:
    resp = client.get("/api/v1/videos", params={"limit": 100})
    resp.raise_for_status()
    videos = resp.json()["videos"]
    name_to_id: dict[str, str] = {v["filename"]: v["id"] for v in videos}

    ids: list[str] = []
    for fn in filenames:
        if fn not in name_to_id:
            print(
                f"ERROR: Video '{fn}' not found in library. "
                "Ensure videos are in the specified directory.",
                file=sys.stderr,
            )
            sys.exit(1)
        ids.append(name_to_id[fn])
    return ids
```

### `poll_render_job(client, job_id)`

Polls the render job until it reaches `completed`, `failed`, or `cancelled`, or until the 120-second timeout expires. The seed script exits non-zero on failure or timeout.

```python
def poll_render_job(client: httpx.Client, job_id: str) -> None:
    for _ in range(240):  # 120 seconds max (240 * 0.5s)
        poll_resp = client.get(f"/api/v1/render/{job_id}")
        poll_resp.raise_for_status()
        status = poll_resp.json()["status"]
        if status == "completed":
            print(f"Render job {job_id} completed successfully.")
            return
        elif status in ("failed", "cancelled"):
            print(
                f"ERROR: Render job {job_id} reached terminal status: {status}. "
                "Check render logs for details.",
                file=sys.stderr,
            )
            sys.exit(1)
        time.sleep(0.5)

    print(
        f"ERROR: Render job {job_id} did not reach terminal state within 120 seconds timeout.",
        file=sys.stderr,
    )
    sys.exit(2)
```

### `seed_project(client, video_ids) → SeedResult`

Creates the full project: project record, 4 clips, 5 effects, 1 transition, and queues a render job. Returns a `SeedResult` with all created IDs.

```python
def seed_project(client: httpx.Client, video_ids: list[str]) -> SeedResult:
    # 1. Create project with output settings
    resp = client.post("/api/v1/projects", json={
        "name": PROJECT_NAME,
        "output_width": 1280,
        "output_height": 720,
        "output_fps": 30,
    })
    resp.raise_for_status()
    project_id = resp.json()["id"]

    # 2. Add clips (in_point/out_point/timeline_position are integer frames)
    clip_ids: list[str] = []
    for video_idx, in_pt, out_pt, tl_pos in CLIP_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_ids[video_idx],
                "in_point": in_pt,
                "out_point": out_pt,
                "timeline_position": tl_pos,
            },
        )
        resp.raise_for_status()
        clip_ids.append(resp.json()["id"])

    # 2b. Create a default video track and assign clips to it
    fps = 30
    resp = client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "Video Track 1", "z_index": 0,
               "muted": False, "locked": False}],
    )
    resp.raise_for_status()
    track_id = resp.json()["tracks"][0]["id"]

    for i, (_, in_pt, out_pt, tl_pos) in enumerate(CLIP_DEFS):
        tl_start = tl_pos / fps
        tl_end = tl_start + (out_pt - in_pt) / fps
        resp = client.post(
            f"/api/v1/projects/{project_id}/timeline/clips",
            json={"clip_id": clip_ids[i], "track_id": track_id,
                  "timeline_start": tl_start, "timeline_end": tl_end},
        )
        resp.raise_for_status()

    # 3. Apply effects
    effects_applied = 0
    for clip_idx, effect_type, params in EFFECT_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_ids[clip_idx]}/effects",
            json={"effect_type": effect_type, "parameters": params},
        )
        resp.raise_for_status()
        effects_applied += 1

    # 4. Apply transitions
    transitions_applied = 0
    for src_idx, tgt_idx, trans_type, params in TRANSITION_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/effects/transition",
            json={
                "source_clip_id": clip_ids[src_idx],
                "target_clip_id": clip_ids[tgt_idx],
                "transition_type": trans_type,
                "parameters": params,
            },
        )
        resp.raise_for_status()
        transitions_applied += 1

    # 5. Queue render job with public vocabulary render_plan
    # total_duration: max(timeline_end) across all clips, in seconds
    total_duration = max(tl_pos + (out_pt - in_pt) for _, in_pt, out_pt, tl_pos in CLIP_DEFS) / fps
    render_plan: dict[str, object] = {
        "settings": {"quality_preset": "standard"},  # draft | standard | high
        "total_duration": total_duration,
    }
    resp = client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": json.dumps(render_plan)},
    )
    if resp.status_code != 201:
        print(f"ERROR: Render failed with status {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    job_id = resp.json()["id"]
    poll_render_job(client, job_id)

    return SeedResult(
        project_id=project_id,
        video_ids=video_ids,
        clip_ids=clip_ids,
        effects_applied=effects_applied,
        transitions_applied=transitions_applied,
        job_id=job_id,
    )
```

### `verify_project(client, result)`

Reads back the project and clips via API and asserts they match expectations.

```python
def verify_project(client: httpx.Client, result: SeedResult) -> None:
    # Check project
    resp = client.get(f"/api/v1/projects/{result.project_id}")
    resp.raise_for_status()
    proj = resp.json()
    assert proj["name"] == PROJECT_NAME
    assert proj["output_width"] == 1280
    assert proj["output_height"] == 720
    assert proj["output_fps"] == 30

    # Check clips
    resp = client.get(f"/api/v1/projects/{result.project_id}/clips")
    resp.raise_for_status()
    clips_data = resp.json()
    assert clips_data["total"] == len(CLIP_DEFS), (
        f"Expected {len(CLIP_DEFS)} clips, got {clips_data['total']}"
    )
```

### `print_summary(result)`

Prints a human-readable summary to stdout.

```python
def print_summary(result: SeedResult) -> None:
    print(f"\n{'='*50}")
    print(f"Sample Project '{PROJECT_NAME}' created successfully!")
    print(f"{'='*50}")
    print(f"  Project ID:    {result.project_id}")
    print(f"  Videos used:   {len(result.video_ids)}")
    print(f"  Clips added:   {len(result.clip_ids)}")
    print(f"  Effects:       {result.effects_applied}")
    print(f"  Transitions:   {result.transitions_applied}")
    print(f"  Render job ID: {result.job_id} (status: completed)")
    print("  Output:        1280x720 @ 30fps")
    print("  Duration:      ~46.0s (1380 frames)")
    print(f"{'='*50}\n")
```

### `main()` — Full Flow

```python
def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    videos_dir = str(Path(args.videos_dir).resolve())

    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        # 1. Health check — verify server is reachable
        try:
            resp = client.get("/health/live")
            if resp.status_code != 200:
                print(f"ERROR: Server not reachable at {base_url}", file=sys.stderr)
                sys.exit(1)
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to server at {base_url}", file=sys.stderr)
            sys.exit(1)

        # 2. Check for existing project
        existing_id = find_existing_project(client)
        if existing_id:
            if args.force:
                print(f"Deleting existing sample project {existing_id}...")
                delete_project(client, existing_id)
            else:
                print(f"Sample project already exists (ID: {existing_id}). "
                      f"Use --force to recreate.")
                sys.exit(0)

        # 3. Scan videos (skip if already scanned)
        if videos_already_scanned(client, SAMPLE_VIDEOS):
            print("Videos already scanned — skipping scan_and_wait().")
        else:
            print(f"Scanning videos from {videos_dir}...")
            scan_and_wait(client, videos_dir)

        # 4. Resolve video IDs from filenames
        video_ids = resolve_video_ids(client, SAMPLE_VIDEOS)

        # 5. Seed the project (create project, clips, effects, transitions, render job)
        print("Creating sample project...")
        result = seed_project(client, video_ids)

        # 6. Verify the project was created correctly
        print("Verifying...")
        verify_project(client, result)

        # 7. Print summary
        print_summary(result)


if __name__ == "__main__":
    main()
```

## Error Handling Approach

| Error | Source | Handling |
|-------|--------|----------|
| `httpx.HTTPStatusError` | Any non-2xx API response | Raised by `resp.raise_for_status()`. Full response body visible in traceback. |
| `httpx.ConnectError` | Server not reachable | Health check at start catches this with a clear error message. |
| Missing videos | Scan didn't find expected files | `resolve_video_ids()` exits with "Video 'X' not found" error. |
| Project already exists | Name collision | `find_existing_project()` checks by name. Without `--force`, exits cleanly. With `--force`, deletes and recreates. |
| Scan failure | Job completes with non-"complete" status | `scan_and_wait()` exits with status message. |
| Scan timeout | Job doesn't complete in 60 seconds | `scan_and_wait()` exits with timeout message. |
| Render failure | Render job reaches `failed` or `cancelled` | `poll_render_job()` exits with status message. |
| Render timeout | Render job doesn't complete in 120 seconds | `poll_render_job()` exits with timeout message (exit code 2). |

The script uses `sys.exit(1)` for all error paths (exit code `2` for render timeout) and `sys.exit(0)` for the "already exists, no --force" case. No exceptions propagate to the user except `httpx.HTTPStatusError` from unexpected API failures, which provides full diagnostic information in the traceback.
