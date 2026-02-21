# AI Integration Guide

Stoat & Ferret is designed from the ground up for AI-driven control. The API, effect discovery system, and structured schemas enable AI agents to programmatically edit video through natural language instructions translated into API calls.

## Design Principles

1. **Machine-readable schemas** -- Every effect has a JSON Schema and AI hints that tell an AI agent how to use it correctly.
2. **Predictable REST API** -- Standard HTTP methods, consistent error codes, and pagination make the API easy for code-generation models to target.
3. **Self-documenting** -- The OpenAPI schema at `/openapi.json` provides a complete, machine-readable description of every endpoint.
4. **Non-destructive** -- All operations are reversible. Effects can be previewed, applied, updated, and removed without risk to source files.

## OpenAPI Schema

The full API specification is available at:

```
http://localhost:8000/openapi.json
```

AI agents can fetch this schema to discover all available endpoints, request/response formats, and validation constraints. Many AI frameworks support loading OpenAPI specs directly to generate API bindings.

```bash
curl http://localhost:8000/openapi.json
```

Interactive documentation is also available:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Effect Discovery with AI Hints

The `GET /api/v1/effects` endpoint returns metadata specifically designed for AI consumption. Each effect includes an `ai_hints` dictionary with per-parameter guidance:

```bash
curl http://localhost:8000/api/v1/effects
```

Example response (truncated):

```json
{
  "effects": [
    {
      "effect_type": "text_overlay",
      "name": "Text Overlay",
      "description": "Add text overlays to video with customizable font, position, and styling.",
      "parameter_schema": {
        "type": "object",
        "properties": {
          "text": {"type": "string", "description": "The text to display"},
          "fontsize": {"type": "integer", "default": 48},
          "fontcolor": {"type": "string", "default": "white"},
          "position": {
            "type": "string",
            "enum": ["center", "bottom_center", "top_left", "top_right", "bottom_left", "bottom_right"]
          }
        },
        "required": ["text"]
      },
      "ai_hints": {
        "text": "The text content to overlay on the video",
        "fontsize": "Font size in pixels, typical range 12-72",
        "fontcolor": "Color name (white, yellow) or hex (#FF0000), append @0.5 for transparency",
        "position": "Where to place the text on screen",
        "margin": "Distance from screen edge in pixels, typical range 5-50",
        "font": "Fontconfig font name (e.g., 'monospace', 'Sans', 'Serif')"
      },
      "filter_preview": "drawtext=text='Sample Text':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20"
    }
  ]
}
```

The `ai_hints` provide:
- Practical value ranges (not just schema min/max)
- Usage guidance ("typical range 0.5-3.0")
- Example values ("'monospace', 'Sans', 'Serif'")
- Semantic context ("Values <1 slow down, >1 speed up")

The `filter_preview` shows a concrete FFmpeg filter string generated with default parameters, giving the AI a reference example.

## Programmatic Workflow Example (Python)

Here is a complete workflow using Python and `httpx` to scan videos, create a project, add clips, and apply effects:

```python
import httpx

BASE = "http://localhost:8000"
client = httpx.Client(base_url=BASE, timeout=30.0)

# Step 1: Scan a directory for videos
resp = client.post("/api/v1/videos/scan", json={
    "path": "/media/raw-footage",
    "recursive": True,
})
job_id = resp.json()["job_id"]

# Step 2: Poll until scan completes
import time
while True:
    status = client.get(f"/api/v1/jobs/{job_id}").json()
    if status["status"] in ("complete", "failed", "timeout"):
        break
    time.sleep(1)

print(f"Scan result: {status['result']}")

# Step 3: List available videos
videos = client.get("/api/v1/videos", params={"limit": 100}).json()
print(f"Found {videos['total']} videos")

# Step 4: Create a project
project = client.post("/api/v1/projects", json={
    "name": "AI-Generated Highlight Reel",
    "output_width": 1920,
    "output_height": 1080,
    "output_fps": 30,
}).json()
project_id = project["id"]

# Step 5: Add clips to the timeline
timeline_pos = 0
clip_ids = []

for video in videos["videos"][:3]:  # Use first 3 videos
    # Use first 5 seconds of each video
    fps = video["frame_rate_numerator"] / video["frame_rate_denominator"]
    out_point = min(int(5 * fps), video["duration_frames"])

    clip = client.post(f"/api/v1/projects/{project_id}/clips", json={
        "source_video_id": video["id"],
        "in_point": 0,
        "out_point": out_point,
        "timeline_position": timeline_pos,
    }).json()

    clip_ids.append(clip["id"])
    timeline_pos += out_point

# Step 6: Discover available effects
effects = client.get("/api/v1/effects").json()
effect_types = [e["effect_type"] for e in effects["effects"]]
print(f"Available effects: {effect_types}")

# Step 7: Apply a fade-in to the first clip
client.post(f"/api/v1/projects/{project_id}/clips/{clip_ids[0]}/effects", json={
    "effect_type": "video_fade",
    "parameters": {"fade_type": "in", "duration": 1.0},
})

# Step 8: Add a title overlay to the first clip
client.post(f"/api/v1/projects/{project_id}/clips/{clip_ids[0]}/effects", json={
    "effect_type": "text_overlay",
    "parameters": {
        "text": "Highlight Reel",
        "fontsize": 64,
        "fontcolor": "white",
        "position": "center",
    },
})

# Step 9: Apply a fade-out to the last clip
client.post(f"/api/v1/projects/{project_id}/clips/{clip_ids[-1]}/effects", json={
    "effect_type": "video_fade",
    "parameters": {"fade_type": "out", "duration": 1.5},
})

# Step 10: Add transitions between adjacent clips
for i in range(len(clip_ids) - 1):
    client.post(f"/api/v1/projects/{project_id}/effects/transition", json={
        "source_clip_id": clip_ids[i],
        "target_clip_id": clip_ids[i + 1],
        "transition_type": "xfade",
        "parameters": {"transition": "fade", "duration": 1.0, "offset": 4.0},
    })

# Step 11: Preview an effect before applying
preview = client.post("/api/v1/effects/preview", json={
    "effect_type": "speed_control",
    "parameters": {"factor": 1.5},
}).json()
print(f"Preview filter: {preview['filter_string']}")

# Verify the final timeline
clips = client.get(f"/api/v1/projects/{project_id}/clips").json()
print(f"Timeline has {clips['total']} clips")
for clip in clips["clips"]:
    effects_count = len(clip["effects"]) if clip["effects"] else 0
    print(f"  Clip {clip['id']}: frames {clip['in_point']}-{clip['out_point']}, "
          f"{effects_count} effects")
```

## Async Version (Python)

For integration with async frameworks, use `httpx.AsyncClient`:

```python
import httpx
import asyncio

async def create_edit():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create project
        resp = await client.post("/api/v1/projects", json={
            "name": "Async Edit",
            "output_fps": 30,
        })
        project = resp.json()

        # Discover effects
        effects = await client.get("/api/v1/effects")
        for effect in effects.json()["effects"]:
            print(f"{effect['effect_type']}: {effect['description']}")
            for param, hint in effect["ai_hints"].items():
                print(f"  {param}: {hint}")

asyncio.run(create_edit())
```

## Natural Language to API Translation

An AI agent can translate natural language editing instructions into API calls. Here are example mappings:

| User Instruction | API Call |
|-----------------|----------|
| "Add my intro video at the start" | `POST /api/v1/projects/{id}/clips` with `in_point: 0, timeline_position: 0` |
| "Speed up the second clip to 2x" | `POST .../clips/{clip_id}/effects` with `speed_control, factor: 2.0` |
| "Fade in from black over 2 seconds" | `POST .../clips/{clip_id}/effects` with `video_fade, fade_type: in, duration: 2.0` |
| "Add a title saying 'Chapter 1'" | `POST .../clips/{clip_id}/effects` with `text_overlay, text: "Chapter 1"` |
| "Cross-dissolve between clips" | `POST .../effects/transition` with `xfade, transition: dissolve` |
| "Lower the background music" | `POST .../clips/{clip_id}/effects` with `volume, volume: 0.3` |
| "Make it half speed" | `POST .../clips/{clip_id}/effects` with `speed_control, factor: 0.5` |
| "Fade the audio out at the end" | `POST .../clips/{clip_id}/effects` with `audio_fade, fade_type: out` |

### Translation Strategy

When building an AI agent that translates natural language to API calls:

1. **Fetch the OpenAPI schema** once at startup to understand available endpoints
2. **Fetch the effects list** to get current effect types and parameter schemas
3. **Use AI hints** to select appropriate parameter values
4. **Preview effects** before applying to validate the output
5. **Handle errors** gracefully -- the structured error codes tell you exactly what went wrong

## WebSocket Integration

For real-time feedback, connect to the WebSocket endpoint:

```python
import asyncio
import json
import websockets

async def monitor_events():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        while True:
            message = json.loads(await ws.recv())
            event_type = message["type"]

            if event_type == "scan_completed":
                print(f"Scan finished: {message['payload']}")
            elif event_type == "project_created":
                print(f"New project: {message['payload']}")
            elif event_type != "heartbeat":
                print(f"Event: {event_type}")

asyncio.run(monitor_events())
```

This lets an AI agent react to events (e.g., start adding clips as soon as a scan completes).

## Correlation IDs for Tracing

Include a correlation ID header to trace requests through the system:

```python
headers = {"X-Correlation-ID": "ai-session-001-step-5"}
client.post("/api/v1/projects", json={...}, headers=headers)
```

The correlation ID appears in server logs and WebSocket events, making it easy to debug AI-driven workflows.

## Planned: AI Theater Mode **[Planned]**

A planned feature called "AI Theater Mode" will provide a specialized interface for AI-driven editing sessions. The planned capabilities include:

- **[Planned]** Natural language command input with real-time preview
- **[Planned]** Automatic effect suggestion based on content analysis
- **[Planned]** Conversational editing workflow (describe what you want, see it applied)
- **[Planned]** Undo/redo with natural language (e.g., "undo the last change")

## Next Steps

- [API Reference](03_api-reference.md) -- complete endpoint details for integration
- [Effects Guide](04_effects-guide.md) -- all effects with parameter schemas and AI hints
- [API Overview](02_api-overview.md) -- error handling, pagination, and conventions
