# Sample Project: Running Montage

A pre-built editing project that demonstrates clips with in/out points, video effects (fade, text overlay, speed control), crossfade transitions, and timeline composition — using the video files included in the repository.

Use it as a development reference, testing anchor, or onboarding aid.

## Prerequisites

- stoat-and-ferret server running locally (see [Development Setup](../02_development-setup.md))
- Python 3.10+
- `httpx` installed (available via `uv sync` — no separate install needed)
- Video files present in the `videos/` directory (included in the repository)

## Quick Start

Seed the sample project against your running server:

```bash
python scripts/seed_sample_project.py http://localhost:8765
```

Options:

- `--videos-dir <path>` — Path to the video files directory (default: `./videos`)
- `--force` — Delete an existing "Running Montage" project and recreate it

Open the GUI to see the result:

```
http://localhost:8765/gui/projects
```

Expected output:

```
Scanning videos from /path/to/videos...
Creating sample project...
Verifying...

==================================================
Sample Project 'Running Montage' created successfully!
==================================================
  Project ID:    <uuid>
  Videos used:   4
  Clips added:   4
  Effects:       5
  Transitions:   1
  Output:        1280x720 @ 30fps
  Duration:      ~46.0s (1380 frames)
==================================================
```

## What Gets Created

### Videos Imported

All 6 videos in `videos/` are scanned into the library. The sample project uses 4 of them:

| # | Filename | Duration | Resolution | FPS |
|---|----------|----------|------------|-----|
| 1 | `78888-568004778_medium.mp4` | 29.73s | 1280x720 | 60 |
| 2 | `running1.mp4` | 29.60s | 960x540 | 30 |
| 3 | `running2.mp4` | 22.32s | 960x540 | 29.97 |
| 4 | `81872-577880797_medium.mp4` | 50.99s | 1280x720 | 60 |

The remaining 2 videos (`120449-720880553_medium.mp4`, `15748-266043652_medium.mp4`) are available in the library for other projects.

### Project Structure

- **Name:** Running Montage
- **Output:** 1280x720 @ 30fps
- **Duration:** ~46.0 seconds (1380 frames)

### Clips

All in/out point and timeline position values are integer frame counts at the 30fps project output rate.

| Clip | Source Video | In (frames) | Out (frames) | Timeline Pos (frames) | Duration |
|------|-------------|-------------|--------------|----------------------|----------|
| 1 | `78888-568004778_medium.mp4` | 60 | 300 | 0 | 8.0s |
| 2 | `running1.mp4` | 90 | 540 | 300 | 15.0s |
| 3 | `running2.mp4` | 30 | 360 | 750 | 11.0s |
| 4 | `81872-577880797_medium.mp4` | 150 | 450 | 1080 | 10.0s |

### Effects

| Clip | Effect Type | Parameters | Purpose |
|------|------------|------------|---------|
| 1 | `video_fade` | `fade_type: in, start_time: 0.0, duration: 1.0` | Fade-in from black (1s) |
| 1 | `text_overlay` | `text: "Running Montage", fontsize: 64, fontcolor: white` | Title card |
| 2 | `speed_control` | `factor: 0.75` | Slow-motion |
| 4 | `text_overlay` | `text: "The End", fontsize: 48, fontcolor: white` | Outro title |
| 4 | `video_fade` | `fade_type: out, start_time: 8.0, duration: 2.0` | Fade-out to black (2s) |

### Transitions

| Between | Type | Parameters |
|---------|------|------------|
| Clip 2 → Clip 3 | `xfade` | `transition: fade, duration: 1.0` |

### Timeline Diagram

```
Timeline (30 fps, total 1380 frames / 46.0s)

Frame:  0        300       750       1080      1380
        |         |         |         |         |
        |--Clip 1-|---Clip 2---|--Clip 3--|--Clip 4--|
        |  8.0s   |   15.0s    |  11.0s   |  10.0s   |
        |         |            |          |          |
Effects:|         |            |          |          |
  fade-in (1s)   |            |          |          |
  "Running       |            |          | "The End"|
   Montage"      |            |          | fade-out |
   title         speed 0.75x  |          |  (2s)    |
                              |          |
                        xfade (1s)       |
                     (Clip 2 → Clip 3)   |
```

## Exploring the Project

### GUI

Navigate to the Projects page and click "Running Montage" to view the timeline, clips, and effects.

### API

List all projects:

```bash
curl http://localhost:8765/api/v1/projects | python -m json.tool
```

Inspect clips for a project (replace `{project_id}` with the actual ID):

```bash
curl http://localhost:8765/api/v1/projects/{project_id}/clips | python -m json.tool
```

View effects on a specific clip:

```bash
curl http://localhost:8765/api/v1/projects/{project_id}/clips/{clip_id}/effects | python -m json.tool
```

Browse the effect catalog:

```bash
curl http://localhost:8765/api/v1/effects | python -m json.tool
```

See the [API Reference](../../manual/03_api-reference.md) for full endpoint documentation.

## Resetting the Sample Project

Delete and recreate:

```bash
python scripts/seed_sample_project.py http://localhost:8765 --force
```

Or delete manually via API:

```bash
curl -X DELETE http://localhost:8765/api/v1/projects/{project_id}
```

Scanned videos persist in the library after project deletion. Only the project, its clips, and their effects are removed.

## For Developers

### Modifying the Sample Project

Edit the constants in `scripts/seed_sample_project.py`:

- `CLIP_DEFS` — clip source videos, in/out points, and timeline positions
- `EFFECT_DEFS` — effects applied to clips
- `TRANSITION_DEFS` — transitions between clips

When updating the seed script, also update the `sample_project` fixture in `tests/smoke/conftest.py` which uses the same definitions.

### Cross-References

- [`docs/design/sample_project/`](../../design/sample_project/) — Sample project design documents
- [`docs/design/smoke_test/`](../../design/smoke_test/) — Smoke test design documents
- [`docs/manual/04_effects-guide.md`](../../manual/04_effects-guide.md) — Effect types and parameters
- [`docs/manual/02_api-overview.md`](../../manual/02_api-overview.md) — API overview
- [`scripts/seed_sample_project.py`](../../../scripts/seed_sample_project.py) — Seed script source code
- [`tests/smoke/conftest.py`](../../../tests/smoke/conftest.py) — Smoke test fixtures (`sample_project`)
- [`tests/smoke/test_sample_project.py`](../../../tests/smoke/test_sample_project.py) — Sample project regression test
