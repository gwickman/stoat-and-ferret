# C4 Code Level: Compose Module

**Source:** `rust/stoat_ferret_core/src/compose/`
**Component:** Rust Core

## Purpose

Provides composition builders for multi-stream video layouts. Generates FFmpeg overlay and scale filter strings from normalized layout positions, and builds complete composition graphs from multi-clip configurations.

## Module Structure

The compose module consists of three submodules with a registration pattern:

- `graph` — Composition graph builder (primary entry point)
- `overlay` — Overlay and scale filter helpers
- `timeline` — Composition timeline builders

All submodules implement a `register(m: &Bound<PyModule>) -> PyResult<()>` function to expose their types and functions to Python.

## Public Interface

### graph Submodule

**Primary Entry Point:**

- **`build_composition_graph(clips: Vec<Clip>, preset: LayoutPreset, output_width: u32, output_height: u32, fps: FrameRate) -> Result<CompositionGraph, CompositionError>`**
  - Builds a complete composition graph from multiple clips
  - Uses preset layout positions to determine stream positioning
  - Handles multi-stream scaling and overlaying
  - Returns complete FFmpeg filter graph string
  - Raises `CompositionError` if clips invalid or incompatible

**CompositionGraph Type:**
- Represents a complete multi-stream composition
- Methods: `to_filter_string() -> String` — Generate FFmpeg filter_complex argument
- Fields: input count, output format, filter graph

**CompositionError Enum:**
- `InvalidClipCount { expected: usize, got: usize }` — Wrong number of clips for preset
- `ClipValidationFailed(Vec<ClipValidationError>)` — Clip validation errors
- `FilterGenerationFailed(String)` — FFmpeg filter generation error

### overlay Submodule

**Filter Builders:**

- **`build_overlay_filter(source_input: usize, overlay_input: usize, position: &LayoutPosition, output_width: u32, output_height: u32) -> Filter`**
  - Creates overlay filter for one stream over another
  - Uses normalized position coordinates, converts to pixels
  - Returns `Filter` suitable for FilterGraph

- **`build_scale_filter(input_index: usize, position: &LayoutPosition, output_width: u32, output_height: u32) -> Filter`**
  - Creates scale filter for one stream
  - Scales to position width/height at given output resolution
  - Returns `Filter` with scale parameters

**Helpers:**
- **`get_overlay_filter_string(source_label: &str, overlay_label: &str, x: i32, y: i32) -> String`**
  - Generate overlay filter string with pixel coordinates
  - Format: `[source][overlay]overlay=x={x}:y={y}[out]`

- **`get_scale_filter_string(width: i32, height: i32) -> String`**
  - Generate scale filter string
  - Format: `scale={width}:{height}`

### timeline Submodule

**Timeline-Aware Builders:**

- **`build_composition_timeline(clips: Vec<Clip>, fps: FrameRate) -> CompositionTimeline`**
  - Creates timeline structure for clip composition
  - Tracks clip positions and durations
  - Validates temporal alignment

- **`CompositionTimeline` Type:**
  - `clips: Vec<ClipOnTimeline>` — Positioned clips
  - `total_duration: Duration` — Output duration
  - `fps: FrameRate` — Frame rate

- **`ClipOnTimeline` Type:**
  - `clip: Clip` — Original clip data
  - `timeline_position: Position` — Where clip starts on output timeline
  - `duration: Duration` — Actual duration on timeline

## Type Registration

The module's `#[pymodule]` registration (via lib.rs `compose` module access) exposes:

1. **CompositionGraph** — Main builder output type
2. **CompositionError** — Error type for graph building
3. **LayoutPosition** — Position references
4. **build_composition_graph()** — Primary entry point

Additional types accessible via submodule registration:
- Filter builders (overlay, scale)
- Timeline composition types
- Helper functions

## Dependencies

### Internal Crate Dependencies

- `clip` — Clip type and validation
- `clip::validation` — ClipValidationError
- `ffmpeg::filter` — Filter, FilterChain, FilterGraph types
- `layout::position` — LayoutPosition normalization and conversion
- `layout::preset` — LayoutPreset enum and specifications
- `timeline` — Position, Duration, FrameRate for temporal calculations
- `sanitize` — Input escaping for filter parameters

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support

## Key Implementation Details

### Graph Building Pipeline

1. **Input Validation:**
   - Validate all clips (delegates to `clip::validation::validate_clips`)
   - Verify clip count matches preset

2. **Layout Resolution:**
   - Get layout positions from preset
   - Convert normalized coordinates to pixels based on output resolution

3. **Filter Generation:**
   - For each clip, generate scale filter to position dimensions
   - Stack filters with overlay filters respecting z_index
   - Create FilterGraph with all filters and stream mappings

4. **Output:**
   - Return CompositionGraph with:
     - Complete filter_complex string
     - Input/output mapping
     - Frame rate and resolution info

### Stream Label Convention

FFmpeg filter graphs use labeled streams:
- Input labels: `0:v` (video stream 0), `1:v` (video stream 1), etc.
- Filter outputs: `[scaled0]`, `[overlay1]`, etc.
- Final output: `[out]`

### Resolution-Independent Composition

The process preserves resolution independence:
1. Clips use frame counts (not pixels)
2. Layout positions use normalized coordinates (0.0-1.0)
3. Conversion to pixels happens at graph building time
4. FFmpeg handles scaling and compositing

### Temporal Alignment

Multiple approaches for timeline composition:

**Synchronous (all clips start together):**
```python
clips = [clip1, clip2, clip3]
graph = build_composition_graph(clips, LayoutPreset.grid_2x2, 1920, 1080, fps)
```

**Staggered (clips at different timeline positions):**
- Use CompositionTimeline to position clips
- Each clip has both duration and timeline_position
- Output duration = max timeline_position + clip duration

## Relationships

**Used by:**
- Python composition UI — Builds filter graphs from user-selected clips and presets
- Timeline rendering — Generates FFmpeg arguments for multi-clip output
- Preview generation — Creates composition previews at various resolutions

**Uses:**
- `clip` module — Clip representation and validation
- `ffmpeg::filter` — Filter graph types for string generation
- `layout` module — Position normalization and preset definitions
- `timeline` module — Frame-accurate positioning
- `sanitize` module — Parameter escaping

## Testing

Comprehensive test coverage includes:

1. **Graph building tests:**
   - PIP compositions (2 clips)
   - Side-by-side (2 clips)
   - Grid 2×2 (4 clips)
   - Correct filter chain generation

2. **Validation tests:**
   - Clip count vs preset matching
   - Invalid clip detection
   - Error propagation

3. **Filter generation tests:**
   - Scale filter strings
   - Overlay filter strings with correct coordinates
   - Z-index ordering in filter chains

4. **Resolution tests:**
   - Pixel conversion at various resolutions
   - Asymmetry handling at odd resolutions

5. **Timeline composition tests:**
   - Synchronous multi-clip alignment
   - Staggered positioning
   - Total duration calculation

## Notes

- **FFmpeg Filter Complexity:** Complex compositions with many overlays may hit FFmpeg complexity limits. Break into stages (e.g., scale first, then overlay).
- **Audio in Compositions:** Currently composition module focuses on video scaling and overlaying. Audio mixing handled separately by `ffmpeg::audio` module.
- **GPU Acceleration:** Scaled filters can use GPU acceleration (-init_hw_device) for performance improvement.
- **Codec-Specific Optimizations:** Some codecs (hevc_nvenc, h264_nvenc) may benefit from different scale filter approaches.

## Example Usage

```python
from stoat_ferret_core import (
    Clip, LayoutPreset, FrameRate, Position,
    build_composition_graph
)

# Create clips
clip1 = Clip("video1.mp4", Position.from_secs(0, fps), Position.from_secs(10, fps), None)
clip2 = Clip("video2.mp4", Position.from_secs(0, fps), Position.from_secs(10, fps), None)

fps = FrameRate.fps_24()
clips = [clip1, clip2]

# Build 2×2 grid composition
graph = build_composition_graph(
    clips,
    LayoutPreset.grid_2x2,
    output_width=1920,
    output_height=1080,
    fps=fps
)

# Generate FFmpeg filter_complex argument
filter_str = graph.to_filter_string()
# Usage: FFmpegCommand().filter_complex(filter_str)...
```
