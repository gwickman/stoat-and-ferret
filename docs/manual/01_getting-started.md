# Getting Started

This guide walks you through starting the Stoat & Ferret server, accessing the web GUI, and performing basic operations via the REST API.

## Prerequisites

Before proceeding, ensure you have completed the installation steps from the project setup documentation:

1. Python 3.10+ installed
2. Rust toolchain installed (for the PyO3 native extension)
3. FFmpeg installed and available on `PATH`
4. Project dependencies installed:
   ```bash
   pip install -e ".[dev]"
   maturin develop
   ```

## Starting the Server

Launch the API server with:

```bash
python -m stoat_ferret.api
```

The server starts on `http://localhost:8000` by default. You can configure the host and port using environment variables:

```bash
STOAT_API_HOST=0.0.0.0 STOAT_API_PORT=9000 python -m stoat_ferret.api
```

All settings use the `STOAT_` prefix and can also be placed in a `.env` file. See [API Overview](02_api-overview.md) for the full settings reference.

## Verify the Server is Running

Check the liveness endpoint:

```bash
curl http://localhost:8000/health/live
```

Expected response:

```json
{"status": "ok"}
```

Check that all dependencies (database and FFmpeg) are healthy:

```bash
curl http://localhost:8000/health/ready
```

Expected response:

```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 0.12},
    "ffmpeg": {"status": "ok", "version": "6.0"}
  }
}
```

## Access the Web GUI

Open your browser and navigate to:

```
http://localhost:8000/gui/
```

The GUI provides a Dashboard, Library browser, Projects page, and Effect Workshop. See the [GUI Guide](06_gui-guide.md) for details.

> **Note:** Due to SPA routing, always navigate to `/gui/` first, then use in-app links. Direct URL navigation to sub-pages (e.g., `/gui/library`) may not work without the SPA fallback in place.

## Your First API Workflow

The typical workflow is: scan videos into the library, create a project, add clips, and apply effects.

### Step 1: Scan Videos into the Library

Submit a scan job to discover video files in a directory:

```bash
curl -X POST http://localhost:8000/api/v1/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/videos", "recursive": true}'
```

Response (HTTP 202):

```json
{"job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

The scan runs asynchronously. Poll the job status:

```bash
curl http://localhost:8000/api/v1/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Response when complete:

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "complete",
  "result": {"scanned": 15, "new": 15, "updated": 0, "skipped": 0, "errors": []}
}
```

### Step 2: Browse the Video Library

List all discovered videos:

```bash
curl http://localhost:8000/api/v1/videos?limit=5
```

Response:

```json
{
  "videos": [
    {
      "id": "vid-abc123",
      "path": "/path/to/your/videos/interview.mp4",
      "filename": "interview.mp4",
      "duration_frames": 9000,
      "frame_rate_numerator": 30,
      "frame_rate_denominator": 1,
      "width": 1920,
      "height": 1080,
      "video_codec": "h264",
      "audio_codec": "aac",
      "file_size": 52428800,
      "thumbnail_path": "data/thumbnails/vid-abc123.jpg",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 15,
  "limit": 5,
  "offset": 0
}
```

Search for specific videos:

```bash
curl "http://localhost:8000/api/v1/videos/search?q=interview"
```

### Step 3: Create a Project

Create a new editing project with output settings:

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Edit", "output_width": 1920, "output_height": 1080, "output_fps": 30}'
```

Response (HTTP 201):

```json
{
  "id": "proj-xyz789",
  "name": "My First Edit",
  "output_width": 1920,
  "output_height": 1080,
  "output_fps": 30,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

### Step 4: Add a Clip to the Timeline

Add a video clip to your project. All time values are in **frames**, not seconds:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-xyz789/clips \
  -H "Content-Type: application/json" \
  -d '{
    "source_video_id": "vid-abc123",
    "in_point": 0,
    "out_point": 900,
    "timeline_position": 0
  }'
```

This adds the first 30 seconds (900 frames at 30fps) of the video starting at position 0 on the timeline.

Response (HTTP 201):

```json
{
  "id": "clip-def456",
  "project_id": "proj-xyz789",
  "source_video_id": "vid-abc123",
  "in_point": 0,
  "out_point": 900,
  "timeline_position": 0,
  "effects": null,
  "created_at": "2025-01-15T11:05:00Z",
  "updated_at": "2025-01-15T11:05:00Z"
}
```

### Step 5: Apply an Effect

Add a text overlay to the clip:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-xyz789/clips/clip-def456/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "text_overlay",
    "parameters": {
      "text": "Hello World",
      "fontsize": 48,
      "fontcolor": "white",
      "position": "bottom_center"
    }
  }'
```

Response (HTTP 201):

```json
{
  "effect_type": "text_overlay",
  "parameters": {"text": "Hello World", "fontsize": 48, "fontcolor": "white", "position": "bottom_center"},
  "filter_string": "drawtext=text='Hello World':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20"
}
```

## Explore the API

- **Swagger UI** at `http://localhost:8000/docs` -- interactive API explorer
- **ReDoc** at `http://localhost:8000/redoc` -- readable API documentation
- **OpenAPI JSON** at `http://localhost:8000/openapi.json` -- machine-readable schema

## Next Steps

- [API Reference](03_api-reference.md) -- complete endpoint documentation
- [Effects Guide](04_effects-guide.md) -- all 9 available effects with parameter details
- [Timeline Guide](05_timeline-guide.md) -- frame-based clip management
- [GUI Guide](06_gui-guide.md) -- using the web interface
- [AI Integration](08_ai-integration.md) -- programmatic and AI-driven workflows
