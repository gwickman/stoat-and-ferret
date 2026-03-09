# Sample Project Definition: Running Montage

## Name and Purpose

**Name:** "Running Montage"

A pre-defined editing project that demonstrates the core features of stoat-and-ferret — clips with precise in/out points, video effects (fade, text overlay, speed control), and crossfade transitions — using the real video files in `/videos/`.

## Video Selection

Four of the six available videos are used, chosen for a coherent "outdoor/running" narrative:

| Order | Filename | Role | Duration (s) | Resolution | FPS | Frames |
|-------|----------|------|-------------|------------|-----|--------|
| 1 | `78888-568004778_medium.mp4` | Establishing shot (nature/outdoor) | 29.73 | 1280x720 | 60 | 1,784 |
| 2 | `running1.mp4` | Running action, clip 1 | 29.60 | 960x540 | 30 | 888 |
| 3 | `running2.mp4` | Running action, clip 2 | 22.32 | 960x540 | 29.97 | 669 |
| 4 | `81872-577880797_medium.mp4` | Outro/conclusion | 50.99 | 1280x720 | 60 | 3,059 |

### Excluded Videos

| Filename | Duration (s) | Why Excluded |
|----------|-------------|--------------|
| `120449-720880553_medium.mp4` | 35.84 | Does not fit the running/outdoor narrative; kept as additional test data |
| `15748-266043652_medium.mp4` | 28.93 | Does not fit the running/outdoor narrative; kept as additional test data |

The two excluded videos remain in `/videos/` and are scanned into the library. They are available for other projects and for smoke test assertions (UC-1 verifies all 6 videos are scanned).

## Clip Definitions

All `in_point`, `out_point`, and `timeline_position` values are **integer frame counts** at the project output frame rate (30 fps). The API's `ClipCreate` schema defines these as `int` fields.

| Clip | Source Video | In (s) | Out (s) | In (frames) | Out (frames) | Timeline Pos (frames) | Duration (s) |
|------|-------------|--------|---------|-------------|--------------|----------------------|-------------|
| 1 | `78888-568004778_medium.mp4` | 2.0 | 10.0 | 60 | 300 | 0 | 8.0 |
| 2 | `running1.mp4` | 3.0 | 18.0 | 90 | 540 | 300 | 15.0 |
| 3 | `running2.mp4` | 1.0 | 12.0 | 30 | 360 | 750 | 11.0 |
| 4 | `81872-577880797_medium.mp4` | 5.0 | 15.0 | 150 | 450 | 1080 | 10.0 |

**Notes:**
- All in/out points are well within each source video's actual duration, providing safe margins.
- The frame numbers assume the 30 fps project output rate for timeline positioning.
- Source videos may have different native frame rates (25, 29.97, 30, 60 fps); the API handles frame rate conversion internally.

## Effects

| Clip | Effect Type | Parameters | Purpose |
|------|------------|------------|---------|
| 1 | `fade` (video) | `{"type": "in", "start_time": 0.0, "duration": 1.0}` | Fade-in from black at the start |
| 1 | `drawtext` | `{"text": "Running Montage", "fontsize": 64, "fontcolor": "white"}` | Title card overlay |
| 2 | `speed` | `{"factor": 0.75}` | Slow-motion running footage |
| 4 | `drawtext` | `{"text": "The End", "fontsize": 48, "fontcolor": "white"}` | Outro title overlay |
| 4 | `fade` (video) | `{"type": "out", "start_time": 8.0, "duration": 2.0}` | Fade-out to black at the end |

Effects are applied via `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` with the body `{"effect_type": "<type>", "parameters": {...}}`.

## Transitions

| Between | Transition Type | Parameters | Purpose |
|---------|----------------|------------|---------|
| Clip 2 → Clip 3 | `fade` (xfade) | `{"duration": 1.0}` | Smooth crossfade between the two running clips |

Applied via `POST /api/v1/projects/{project_id}/effects/transition` with:
```json
{
  "source_clip_id": "<clip_2_id>",
  "target_clip_id": "<clip_3_id>",
  "transition_type": "fade",
  "parameters": {"duration": 1.0}
}
```

## Output Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| `output_width` | 1280 | Matches the majority of source videos (720p). The two 960x540 clips will be upscaled. |
| `output_height` | 720 | Matches the majority of source videos (720p). |
| `output_fps` | 30 | Common denominator across all source frame rates (25, 29.97, 30, 60). |

## Total Composition Duration

| Clip | Duration | Timeline Range (frames) |
|------|----------|------------------------|
| Clip 1 | 8.0s | 0–300 |
| Clip 2 | 15.0s (speed 0.75x → visual duration 20.0s) | 300–750 |
| Clip 3 | 11.0s | 750–1080 |
| Clip 4 | 10.0s | 1080–1380 |

**Total timeline duration:** 1380 frames = 46.0 seconds at 30 fps

The speed effect on Clip 2 changes the visual playback speed but does not alter the timeline frame positions. The in/out points define the source material range; the speed factor affects how that material is played back in the rendered output.

## ASCII Timeline Diagram

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

Source videos:
  Clip 1: 78888-568004778_medium.mp4  [frames 60-300, 1280x720 @ 60fps]
  Clip 2: running1.mp4               [frames 90-540, 960x540  @ 30fps]
  Clip 3: running2.mp4               [frames 30-360, 960x540  @ 29.97fps]
  Clip 4: 81872-577880797_medium.mp4  [frames 150-450, 1280x720 @ 60fps]
```
