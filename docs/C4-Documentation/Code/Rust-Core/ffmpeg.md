# C4 Code Level: FFmpeg Module

**Source:** `rust/stoat_ferret_core/src/ffmpeg/`
**Component:** Rust Core

## Purpose

Provides type-safe builders for constructing FFmpeg command arguments, filter graphs, and specialized encoding/effects parameters (video speed, audio mixing, text overlays, transitions). Builders create argument arrays suitable for `std::process::Command` without shell escaping.

## Public Interface

### Command Builder

#### `FFmpegCommand`
Builder for constructing FFmpeg argument vectors.

**Methods (builder pattern - all return self for chaining):**

**Global Options:**
- `new() -> Self` — Create empty command builder
- `overwrite(yes: bool) -> Self` — Add `-y` flag for overwrite
- `loglevel(level: impl Into<String>) -> Self` — Set `-loglevel` (quiet, panic, fatal, error, warning, info, verbose, debug)

**Input Management:**
- `input(path: impl Into<String>) -> Self` — Add input file with `-i`
- `seek(seconds: f64) -> Self` — Set `-ss` seek position for most recent input
- `duration(seconds: f64) -> Self` — Set `-t` duration limit for most recent input
- `stream_loop(count: i32) -> Self` — Set `-stream_loop` for most recent input

**Output Management:**
- `output(path: impl Into<String>) -> Self` — Add output file
- `video_codec(codec: impl Into<String>) -> Self` — Set `-c:v` video codec for most recent output
- `audio_codec(codec: impl Into<String>) -> Self` — Set `-c:a` audio codec for most recent output
- `preset(preset: impl Into<String>) -> Self` — Set `-preset` for most recent output
- `crf(crf: u8) -> Self` — Set `-crf` quality (0-51) for most recent output
- `format(format: impl Into<String>) -> Self` — Set `-f` output format
- `map(stream: impl Into<String>) -> Self` — Add `-map` stream mapping

**Filtering:**
- `filter_complex(filter: impl Into<String>) -> Self` — Set `-filter_complex` for complex filter graphs

**Build:**
- `build() -> Result<Vec<String>, CommandError>` — Generate argument vector with validation

**Validation (automatic on build()):**
- At least one input file required → `CommandError::NoInputs`
- At least one output file required → `CommandError::NoOutputs`
- No empty paths allowed → `CommandError::EmptyPath`
- CRF in range 0-51 → `CommandError::InvalidCrf(u8)`

#### `CommandError`
Enum for FFmpeg command building errors:
- `NoInputs` — "At least one input file is required"
- `NoOutputs` — "At least one output file is required"
- `EmptyPath` — "File path cannot be empty"
- `InvalidCrf(u8)` — "CRF value {crf} is out of range (must be 0-51)"

### Filter Types

#### `Filter`
Single FFmpeg filter representation.

**Methods:**
- `name() -> &str` — Filter name (e.g., "scale", "fade")
- `params() -> &FilterParams` — Filter parameters

#### `FilterChain`
Sequence of filters applied to one stream.

**Methods:**
- `input(label: impl Into<String>) -> Self` — Set input stream label [in]
- `filter(filter: Filter) -> Self` — Add filter to chain
- `output(label: impl Into<String>) -> Self` — Set output stream label [out]
- `to_string() -> String` — Generate filter chain string (e.g., "[0:v]scale[scaled]")

#### `FilterGraph`
Complete filter graph with multiple chains for complex operations.

**Methods:**
- `new() -> Self` — Create empty graph
- `chain(chain: FilterChain) -> Self` — Add filter chain
- `to_string() -> String` — Generate complete filter graph string

### Filter Helper Functions

- `py_scale_filter(width: u32, height: u32) -> Filter` — Create scale filter
- `py_concat_filter(video_count: u32, audio_count: u32) -> Filter` — Create concat filter

### Video Effects Builders

#### `SpeedControl`
Video speed/tempo adjustment builder.

**Methods:**
- `new(speed_multiplier: f64) -> Self` — Create with speed (0.25-4.0)
- `to_filter() -> Filter` — Generate setpts filter

#### `DrawtextBuilder`
Text overlay builder using FFmpeg drawtext filter.

**Methods:**
- `new(text: String, x: f64, y: f64, fontsize: u32) -> Self`
- `font(path: impl Into<String>) -> Self` — Set font file path
- `fontcolor(color: impl Into<String>) -> Self` — Set font color (hex or name)
- `borderw(width: u32) -> Self` — Set border width
- `bordercolor(color: impl Into<String>) -> Self` — Set border color
- `to_filter() -> Filter` — Generate drawtext filter

### Audio Builders

#### `VolumeBuilder`
Audio volume adjustment builder.

**Methods:**
- `new(volume: f64) -> Self` — Create with volume multiplier (0.0-10.0)
- `to_filter() -> Filter` — Generate volume filter

#### `AfadeBuilder`
Audio fade-in/fade-out builder.

**Methods:**
- `new(fade_type: FadeType) -> Self` — Create with FadeType::In or FadeType::Out
- `duration(samples: u32) -> Self` — Set fade duration in samples
- `to_filter() -> Filter` — Generate afade filter

#### `AmixBuilder`
Audio mixing for multiple input streams.

**Methods:**
- `new(input_count: usize) -> Self`
- `weights(weights: Vec<f64>) -> Self` — Set per-input mixing weights
- `to_filter() -> Filter` — Generate amix filter

#### `TrackAudioConfig`
Per-track audio configuration.

**Fields:**
- `track_index: usize` — Which track (0-indexed)
- `volume: f64` — Volume multiplier
- `pan: Option<String>` — Stereo panning

#### `AudioMixSpec`
Complete audio mixing specification.

**Fields:**
- `tracks: Vec<TrackAudioConfig>` — Per-track configurations
- `output_channels: u32` — Mono (1) or Stereo (2)
- `output_sample_rate: u32` — Sample rate in Hz

### Transition Builders

#### `TransitionType`
Enum of available transition types:
- `Fade` — Simple fade effect
- `Xfade` — Cross-fade effect
- `Acrossfade` — Audio cross-fade

#### `FadeBuilder`
Video fade transition (fade in/out).

**Methods:**
- `new(fade_type: FadeType) -> Self`
- `duration_frames(frames: u32) -> Self` — Set fade duration
- `to_filter() -> Filter` — Generate fade filter

#### `XfadeBuilder`
Cross-fade between two video streams.

**Methods:**
- `new(transition_type: TransitionType) -> Self`
- `duration_frames(frames: u32) -> Self` — Set transition duration
- `to_filter() -> Filter` — Generate xfade filter

#### `AcrossfadeBuilder`
Audio cross-fade between two audio streams.

**Methods:**
- `new() -> Self`
- `duration_frames(frames: u32) -> Self` — Set fade duration
- `to_filter() -> Filter` — Generate acrossfade filter

#### `DuckingPattern`
Audio ducking pattern (duck audio under other sounds).

**Fields:**
- `target_db: f64` — Target reduction in dB
- `attack_ms: f64` — Attack time in milliseconds
- `release_ms: f64` — Release time in milliseconds

## Dependencies

### Internal Crate Dependencies

- `sanitize` — Input validation and escaping for filter parameters
- `timeline` — Frame counts and durations for timing calculations

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support

## Key Implementation Details

### Builder Pattern

Commands use method chaining with all methods returning `self`:
```rust
FFmpegCommand::new()
    .overwrite(true)
    .input("in.mp4")
    .seek(5.0)
    .output("out.mp4")
    .video_codec("libx264")
    .crf(23)
    .build()
```

Options apply to the most recently added input/output. Adding a new input resets input-specific options.

### Filter String Syntax

Filters use FFmpeg's filtergraph syntax:
- Stream labels: `[0:v]` (video from input 0), `[0:a]` (audio from input 0)
- Filter chain: `[0:v]scale=1920:1080[scaled]` (input, filter, output label)
- Multiple chains: separated by `;`

### Argument Array Output

`build()` returns `Vec<String>` ready for `std::process::Command`:
```rust
// Not: "ffmpeg -i input.mp4 output.mp4"
// But: vec!["-i", "input.mp4", "output.mp4"]
```

This avoids shell escaping issues and works directly with process spawning.

### CRF Validation

CRF (Constant Rate Factor) for x264/x265:
- Range: 0-51
- 0 = lossless
- 18 = visually lossless
- 23 = default
- 28 = lower quality
- 51 = worst quality

### Filter Safety

User-provided filter parameters (text overlays, audio labels) are sanitized via the `sanitize` module to prevent injection attacks.

## Relationships

**Used by:**
- Composition builders (`compose` module) — Generate complex filter graphs for multi-stream composition
- Python video rendering — Builds commands for subprocess execution
- Timeline composition (`compose::timeline`) — Timing-aware filter building

**Uses:**
- `sanitize` module — For text escaping and codec/preset validation
- `timeline` module — For duration and frame-based timing

## Testing

Comprehensive test suite with 30+ tests including:

1. **Simple transcode** — Basic codec selection
2. **Trim with seek** — Seek position and duration
3. **Full encode options** — All codec, preset, CRF combinations
4. **Multiple inputs/outputs** — Stream management
5. **Stream looping** — Loop count handling
6. **Filter complex** — Filter graph with mapping
7. **Validation tests:**
   - No inputs error
   - No outputs error
   - Empty path error
   - CRF out of range
   - Valid CRF boundaries (0 and 51)
8. **PyO3 integration tests** — Python callable builders

## Notes

- **No Shell Execution:** Builders return argument arrays, not shell commands. This is safer and more predictable.
- **FFmpeg Path:** The builder does not include "ffmpeg" executable name. Callers provide path via `std::process::Command::new("ffmpeg")`.
- **Seek Position Timing:** `-ss` before `-i` seeks during input reading (faster); `-ss` after `-i` seeks during decoding (slower but more accurate).
- **Filter Order:** Input options (seek, duration) must come before `-i`. Output options come after filter complex but before output path.
- **Stream Mapping:** When using filter_complex, explicit `-map` is needed to select which filter outputs go to which files.

## Example Usage

```rust
// Build a command that scales video and transcodes
let args = FFmpegCommand::new()
    .overwrite(true)
    .input("input.mp4")
    .seek(10.0)
    .duration(30.0)
    .output("output.mp4")
    .video_codec("libx264")
    .preset("fast")
    .crf(23)
    .filter_complex("[0:v]scale=1280:720[scaled]")
    .map("[scaled]")
    .map("0:a")
    .build()?;

// Execute with std::process::Command
let output = std::process::Command::new("ffmpeg")
    .args(args)
    .output()?;
```
