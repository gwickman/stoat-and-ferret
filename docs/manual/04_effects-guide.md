# Effects Guide

Stoat & Ferret provides 9 built-in effects powered by a Rust core that generates FFmpeg filter strings. Effects are applied non-destructively to clips and can be previewed, stacked, updated, and removed at any time.

## How Effects Work

1. **Discovery** -- Query `GET /api/v1/effects` to see all available effects with their parameter schemas and AI hints.
2. **Preview** -- Use `POST /api/v1/effects/preview` to generate a filter string without modifying any clip.
3. **Apply** -- Use `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` to append an effect to a clip's effect stack.
4. **Update** -- Use `PATCH .../effects/{index}` to change parameters of an existing effect.
5. **Remove** -- Use `DELETE .../effects/{index}` to remove an effect from the stack.

Each effect produces an FFmpeg filter string (e.g., `drawtext=text='Hello':fontsize=48`) that can be used directly in FFmpeg command lines. The Rust core handles safe parameter escaping and filter construction.

## Effect Discovery

The discovery endpoint returns everything an AI agent or developer needs to use an effect:

```bash
curl http://localhost:8000/api/v1/effects
```

Each effect entry includes:

| Field | Description |
|-------|-------------|
| `effect_type` | Key used in API calls (e.g., `text_overlay`) |
| `name` | Human-readable name |
| `description` | What the effect does |
| `parameter_schema` | JSON Schema for parameter validation |
| `ai_hints` | Per-parameter guidance for AI agents |
| `filter_preview` | Example filter string with default values |

---

## Available Effects

### text_overlay

Add text overlays to video with customizable font, position, and styling. Uses FFmpeg's `drawtext` filter.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | Yes | -- | Text to display |
| `fontsize` | integer | No | 48 | Font size in pixels |
| `fontcolor` | string | No | `"white"` | Color name or hex (e.g., `"#FF0000"`, `"yellow@0.5"` for transparency) |
| `position` | string | No | `"bottom_center"` | Position preset: `center`, `bottom_center`, `top_left`, `top_right`, `bottom_left`, `bottom_right` |
| `margin` | integer | No | 10 | Margin from screen edge in pixels |
| `font` | string | No | -- | Fontconfig font name (e.g., `"monospace"`, `"Sans"`) |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "text_overlay",
    "parameters": {
      "text": "Chapter 1",
      "fontsize": 64,
      "fontcolor": "white",
      "position": "center",
      "margin": 20
    }
  }'
```

**Generated filter string:**
```
drawtext=text='Chapter 1':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2
```

---

### speed_control

Adjust video and audio playback speed. Uses FFmpeg's `setpts` filter for video and `atempo` filter chain for audio (automatically split into multiple stages for factors outside the 0.5-2.0 range).

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `factor` | number | Yes | 2.0 | 0.25-4.0 | Speed multiplier (<1 = slower, >1 = faster) |
| `drop_audio` | boolean | No | `false` | -- | Drop audio instead of speed-adjusting it |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "speed_control",
    "parameters": {"factor": 0.5}
  }'
```

**Generated filter string (0.5x speed):**
```
setpts=2.0*PTS; atempo=0.5
```

---

### volume

Adjust audio volume with linear or dB control. Uses FFmpeg's `volume` filter.

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `volume` | number | Yes | 1.0 | 0.0-10.0 | Volume multiplier (0.0 = silent, 1.0 = original, 2.0 = double) |
| `precision` | string | No | `"float"` | `fixed`, `float`, `double` | Calculation precision |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "volume",
    "parameters": {"volume": 0.5, "precision": "float"}
  }'
```

---

### audio_fade

Apply fade in or fade out to audio. Uses FFmpeg's `afade` filter.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `fade_type` | string | Yes | -- | `"in"` (from silence) or `"out"` (to silence) |
| `duration` | number | Yes | 1.0 | Fade duration in seconds (min 0.01) |
| `start_time` | number | No | 0.0 | Start time in seconds |
| `curve` | string | No | `"tri"` | Curve type: `tri`, `qsin`, `hsin`, `esin`, `log`, `ipar`, `qua`, `cub`, `squ`, `cbr`, `par` |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "audio_fade",
    "parameters": {"fade_type": "in", "duration": 2.0, "curve": "qsin"}
  }'
```

---

### video_fade

Apply fade in or fade out to video. Uses FFmpeg's `fade` filter.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `fade_type` | string | Yes | -- | `"in"` (from color) or `"out"` (to color) |
| `duration` | number | Yes | 1.0 | Fade duration in seconds (min 0.01) |
| `start_time` | number | No | 0.0 | Start time in seconds |
| `color` | string | No | `"black"` | Fade color: named color or hex `#RRGGBB` |
| `alpha` | boolean | No | `false` | Fade the alpha channel instead of to/from a color |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "video_fade",
    "parameters": {"fade_type": "out", "duration": 1.5, "color": "black"}
  }'
```

---

### audio_mix

Mix multiple audio input streams into a single output. Uses FFmpeg's `amix` filter.

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `inputs` | integer | Yes | 2 | 2-32 | Number of audio inputs to mix |
| `duration_mode` | string | No | `"longest"` | `longest`, `shortest`, `first` | Output duration strategy |
| `weights` | array of numbers | No | -- | -- | Per-input volume weights (e.g., `[1.0, 0.5]`) |
| `normalize` | boolean | No | `true` | -- | Normalize output volume |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "audio_mix",
    "parameters": {"inputs": 2, "duration_mode": "shortest", "weights": [1.0, 0.3]}
  }'
```

---

### audio_ducking

Automatically lower music volume during speech using sidechain compression. Uses FFmpeg's `sidechaincompress` filter.

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `threshold` | number | No | 0.125 | 0.00098-1.0 | Speech detection sensitivity (lower = more sensitive) |
| `ratio` | number | No | 2.0 | 1.0-20.0 | Compression ratio (higher = more ducking) |
| `attack` | number | No | 20.0 | 0.01-2000.0 | Attack time in milliseconds |
| `release` | number | No | 250.0 | 0.01-9000.0 | Release time in milliseconds |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "audio_ducking",
    "parameters": {"threshold": 0.1, "ratio": 4.0, "attack": 10.0, "release": 300.0}
  }'
```

---

### xfade (Video Crossfade)

Crossfade between two video inputs with a selectable transition effect. Uses FFmpeg's `xfade` filter. Supports 59 transition types.

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `transition` | string | Yes | `"fade"` | -- | Transition effect name (see list below) |
| `duration` | number | Yes | 1.0 | 0-60 | Transition duration in seconds |
| `offset` | number | Yes | 0.0 | 0+ | When the transition starts relative to first input |

**Common transition names:** `fade`, `wipeleft`, `wiperight`, `wipeup`, `wipedown`, `dissolve`, `pixelize`, `circleopen`, `circleclose`, `slideright`, `slideleft`, `smoothleft`, `smoothright`, `diagtl`, `diagtr`, `diagbl`, `diagbr`, `hlslice`, `hrslice`, `vuslice`, `vdslice`, `radial`, `zoomin`, `squeezeh`, `squeezev`, and many more.

**Example (applied as a transition between clips):**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/effects/transition \
  -H "Content-Type: application/json" \
  -d '{
    "source_clip_id": "clip-001",
    "target_clip_id": "clip-002",
    "transition_type": "xfade",
    "parameters": {"transition": "dissolve", "duration": 1.5, "offset": 4.0}
  }'
```

---

### acrossfade (Audio Crossfade)

Crossfade between two audio inputs with configurable fade curves. Uses FFmpeg's `acrossfade` filter.

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `duration` | number | Yes | 1.0 | 0.01-60 | Crossfade duration in seconds |
| `curve1` | string | No | `"tri"` | See list | Fade curve for first input |
| `curve2` | string | No | `"tri"` | See list | Fade curve for second input |
| `overlap` | boolean | No | `true` | -- | Whether inputs overlap during crossfade |

**Curve types:** `tri` (linear), `qsin` (quarter sine), `hsin` (half sine), `esin` (exponential sine), `log`, `ipar`, `qua` (quadratic), `cub` (cubic), `squ` (square root), `cbr` (cubic root), `par` (parabola).

**Example (applied as a transition between clips):**

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/effects/transition \
  -H "Content-Type: application/json" \
  -d '{
    "source_clip_id": "clip-001",
    "target_clip_id": "clip-002",
    "transition_type": "acrossfade",
    "parameters": {"duration": 2.0, "curve1": "qsin", "curve2": "qsin"}
  }'
```

---

## Previewing Effects

Before applying an effect, you can preview the generated filter string:

```bash
curl -X POST http://localhost:8000/api/v1/effects/preview \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "speed_control",
    "parameters": {"factor": 3.0, "drop_audio": true}
  }'
```

Response:

```json
{
  "effect_type": "speed_control",
  "filter_string": "setpts=0.333333*PTS"
}
```

This lets you validate parameters and see the exact FFmpeg filter that will be generated, without modifying any clips.

## Effect Stack Management

Each clip maintains an ordered list of effects (the "effect stack"). Effects are applied in order and can be managed by index (zero-based).

### View a Clip's Effects

```bash
curl http://localhost:8000/api/v1/projects/proj-1/clips/clip-1
```

The `effects` field in the response contains the full stack:

```json
{
  "effects": [
    {"effect_type": "video_fade", "parameters": {"fade_type": "in", "duration": 1.0}, "filter_string": "fade=t=in:d=1.0"},
    {"effect_type": "text_overlay", "parameters": {"text": "Title"}, "filter_string": "drawtext=text='Title':fontsize=48"}
  ]
}
```

### Update an Effect

Change the parameters of effect at index 0:

```bash
curl -X PATCH http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects/0 \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"fade_type": "in", "duration": 2.0}}'
```

The effect type is preserved -- only parameters are updated. The filter string is regenerated from the new parameters.

### Remove an Effect

Delete effect at index 1:

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/proj-1/clips/clip-1/effects/1
```

After deletion, remaining effects shift down to fill the gap.

## Transitions Between Clips

Transitions connect two adjacent clips with a crossfade effect. Use the transition endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/projects/proj-1/effects/transition \
  -H "Content-Type: application/json" \
  -d '{
    "source_clip_id": "clip-001",
    "target_clip_id": "clip-002",
    "transition_type": "xfade",
    "parameters": {"transition": "fade", "duration": 1.0, "offset": 4.0}
  }'
```

**Requirements:**
- Both clips must exist in the same project
- Source and target must be different clips
- Source must immediately precede target in timeline order (adjacency check)
- The timeline must not be empty

For video transitions, use `xfade`. For audio transitions, use `acrossfade`. Pair them together for a complete audio-visual crossfade.

## Effect Workshop (GUI)

The web GUI at `/gui/effects` provides an interactive Effect Workshop with:

- **Clip Selector** -- choose which clip to work with
- **Effect Catalog** -- browse all 9 effects with descriptions
- **Parameter Form** -- configure effect parameters with the appropriate input controls
- **Filter Preview** -- see the generated FFmpeg filter string in real time
- **Effect Stack** -- view, reorder, and manage applied effects

See the [GUI Guide](06_gui-guide.md) for more details.

## Next Steps

- [API Reference](03_api-reference.md) -- complete endpoint documentation
- [Timeline Guide](05_timeline-guide.md) -- clip and project management
- [AI Integration](08_ai-integration.md) -- using effects programmatically with AI agents
