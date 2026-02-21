# Timeline Guide

This guide covers project creation, video library management, and clip-based timeline editing in Stoat & Ferret. The system uses frame-based coordinates for precise editing control.

## Core Concepts

### Frame-Based Coordinates

All time values in Stoat & Ferret are expressed in **frames**, not seconds. This provides frame-accurate editing precision and avoids floating-point rounding issues.

To convert between seconds and frames:

```
frames = seconds * frame_rate
seconds = frames / frame_rate
```

For example, at 30 fps:
- 5 seconds = 150 frames
- 1 minute = 1800 frames
- Frame 900 = 30.0 seconds

The frame rate is stored as a fraction (`frame_rate_numerator` / `frame_rate_denominator`) to support non-integer rates like 29.97 fps (30000/1001).

### Non-Destructive Editing

All edits are non-destructive. Source video files are never modified. Clips reference source videos by ID and specify in/out points and timeline positions. Effects generate FFmpeg filter strings that describe the processing pipeline without altering the original media.

## Video Library

### Scanning for Videos

Before you can add clips to a project, you need to scan video files into the library:

```bash
curl -X POST http://localhost:8000/api/v1/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/media", "recursive": true}'
```

The scan runs asynchronously. It:

1. Discovers video files in the specified directory
2. Probes each file with FFmpeg to extract metadata (resolution, codec, duration, frame rate)
3. Generates thumbnail images
4. Stores the metadata in the database

Poll the job status:

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

When complete, the result shows how many files were processed:

```json
{
  "job_id": "...",
  "status": "complete",
  "result": {"scanned": 25, "new": 20, "updated": 5, "skipped": 0, "errors": []}
}
```

### Security: Allowed Scan Roots

By default, scanning is allowed from any directory. For security, configure allowed scan roots:

```bash
STOAT_ALLOWED_SCAN_ROOTS='["/media/videos", "/home/user/clips"]'
```

When configured, scan requests for paths outside these roots receive a `PATH_NOT_ALLOWED` error. An empty list (the default) allows all directories.

### Browsing the Library

List all videos:

```bash
curl "http://localhost:8000/api/v1/videos?limit=20&offset=0"
```

Search by filename or path:

```bash
curl "http://localhost:8000/api/v1/videos/search?q=interview"
```

Get details for a specific video:

```bash
curl http://localhost:8000/api/v1/videos/vid-abc123
```

The `VideoResponse` includes all probed metadata:

```json
{
  "id": "vid-abc123",
  "path": "/media/videos/interview.mp4",
  "filename": "interview.mp4",
  "duration_frames": 54000,
  "frame_rate_numerator": 30,
  "frame_rate_denominator": 1,
  "width": 1920,
  "height": 1080,
  "video_codec": "h264",
  "audio_codec": "aac",
  "file_size": 314572800,
  "thumbnail_path": "data/thumbnails/vid-abc123.jpg",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Removing Videos

Remove from the library database only:

```bash
curl -X DELETE http://localhost:8000/api/v1/videos/vid-abc123
```

Remove from the library and delete the source file from disk:

```bash
curl -X DELETE "http://localhost:8000/api/v1/videos/vid-abc123?delete_file=true"
```

## Projects

A project defines output settings and contains a timeline of clips. Create a project to begin editing.

### Creating a Project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Conference Highlights",
    "output_width": 1920,
    "output_height": 1080,
    "output_fps": 30
  }'
```

**Output settings:**

| Field | Default | Range | Description |
|-------|---------|-------|-------------|
| `output_width` | 1920 | >= 1 | Output video width in pixels |
| `output_height` | 1080 | >= 1 | Output video height in pixels |
| `output_fps` | 30 | 1-120 | Output frame rate |

Choose output settings that match your target delivery format. Common presets:

| Preset | Width | Height | FPS |
|--------|-------|--------|-----|
| 1080p/30 | 1920 | 1080 | 30 |
| 1080p/60 | 1920 | 1080 | 60 |
| 4K/30 | 3840 | 2160 | 30 |
| 720p/30 | 1280 | 720 | 30 |
| Vertical/30 | 1080 | 1920 | 30 |

### Managing Projects

List all projects:

```bash
curl http://localhost:8000/api/v1/projects
```

Get a specific project:

```bash
curl http://localhost:8000/api/v1/projects/proj-xyz789
```

Delete a project:

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/proj-xyz789
```

## Clips

Clips are the building blocks of a timeline. Each clip references a source video and specifies which portion to use and where to place it.

### Adding Clips

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-xyz789/clips \
  -H "Content-Type: application/json" \
  -d '{
    "source_video_id": "vid-abc123",
    "in_point": 300,
    "out_point": 1200,
    "timeline_position": 0
  }'
```

**Clip fields (all in frames):**

| Field | Description |
|-------|-------------|
| `source_video_id` | ID of the video from the library |
| `in_point` | First frame to include from the source video |
| `out_point` | Last frame to include from the source video |
| `timeline_position` | Where this clip starts on the project timeline |

In this example, at 30 fps, the clip starts at the 10-second mark of the source video (frame 300) and ends at the 40-second mark (frame 1200), giving a 30-second clip placed at the beginning of the timeline.

### Clip Validation

When you add or update a clip, the Rust core validates:

- `in_point` >= 0
- `out_point` >= 0
- `out_point` does not exceed the source video's `duration_frames`
- The source video file path is valid

If validation fails, you receive a `VALIDATION_ERROR`:

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "out_point 99999 exceeds source video duration of 54000 frames"
  }
}
```

### Building a Multi-Clip Timeline

Here is an example of building a timeline with three clips:

```bash
# Clip 1: Intro (frames 0-900 of video A, starting at timeline position 0)
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips \
  -H "Content-Type: application/json" \
  -d '{"source_video_id": "vid-A", "in_point": 0, "out_point": 900, "timeline_position": 0}'

# Clip 2: Main content (frames 150-4500 of video B, starting at position 900)
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips \
  -H "Content-Type: application/json" \
  -d '{"source_video_id": "vid-B", "in_point": 150, "out_point": 4500, "timeline_position": 900}'

# Clip 3: Outro (frames 0-600 of video C, starting at position 5250)
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips \
  -H "Content-Type: application/json" \
  -d '{"source_video_id": "vid-C", "in_point": 0, "out_point": 600, "timeline_position": 5250}'
```

At 30 fps, this creates:
- 0-30s: Intro from video A
- 30s-175s: Main content from video B
- 175s-195s: Outro from video C

### Updating Clips

Update any combination of `in_point`, `out_point`, and `timeline_position`:

```bash
# Trim the start of clip 2
curl -X PATCH http://localhost:8000/api/v1/projects/proj-1/clips/clip-002 \
  -H "Content-Type: application/json" \
  -d '{"in_point": 300}'

# Move clip 3 to a new timeline position
curl -X PATCH http://localhost:8000/api/v1/projects/proj-1/clips/clip-003 \
  -H "Content-Type: application/json" \
  -d '{"timeline_position": 5400}'
```

Only provided fields are modified. The update is re-validated against the source video.

### Listing Clips

View all clips in a project:

```bash
curl http://localhost:8000/api/v1/projects/proj-1/clips
```

Response:

```json
{
  "clips": [
    {
      "id": "clip-001",
      "project_id": "proj-1",
      "source_video_id": "vid-A",
      "in_point": 0,
      "out_point": 900,
      "timeline_position": 0,
      "effects": null,
      "created_at": "2025-01-15T11:00:00Z",
      "updated_at": "2025-01-15T11:00:00Z"
    },
    {
      "id": "clip-002",
      "project_id": "proj-1",
      "source_video_id": "vid-B",
      "in_point": 150,
      "out_point": 4500,
      "timeline_position": 900,
      "effects": null,
      "created_at": "2025-01-15T11:01:00Z",
      "updated_at": "2025-01-15T11:01:00Z"
    }
  ],
  "total": 2
}
```

### Removing Clips

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/proj-1/clips/clip-002
```

Returns 204 No Content on success.

## Tips

### Converting Timecodes to Frames

If your source material uses timecodes (HH:MM:SS:FF), convert to frame numbers:

```
frame = (hours * 3600 + minutes * 60 + seconds) * fps + frames
```

For example, at 30 fps, timecode `00:01:30:15` = (0 + 0 + 90) * 30 + 15 = 2715 frames.

### Using Different Source Frame Rates

A project has a single output frame rate, but source videos can have different frame rates. The `frame_rate_numerator` and `frame_rate_denominator` fields on each video tell you the source rate. When setting `in_point` and `out_point`, always use the **source video's** frame rate, not the project's output frame rate.

### Clip Ordering

Clips on the timeline are ordered by `timeline_position`. When adding transitions between clips, adjacency is determined by this ordering.

## Planned Features

The following timeline features are planned but not yet implemented:

- **[Planned] Visual Timeline** -- Drag-and-drop timeline canvas in the GUI
- **[Planned] Automatic Gap Detection** -- Warn about gaps or overlaps in the timeline
- **[Planned] Ripple Editing** -- Automatically shift downstream clips when making changes
- **[Planned] Timeline Preview** -- Real-time preview of the assembled timeline

## Next Steps

- [Effects Guide](04_effects-guide.md) -- applying effects and transitions to clips
- [GUI Guide](06_gui-guide.md) -- managing projects and clips through the web interface
- [Rendering Guide](07_rendering-guide.md) -- **[Planned]** exporting the final video
