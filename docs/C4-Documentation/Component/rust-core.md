# Rust Core

## Purpose

The Rust Core component is a native extension module (`stoat_ferret_core`) built with PyO3 and maturin. It provides all compute-intensive operations that benefit from Rust's performance and type safety: frame-accurate timeline mathematics, clip validation, FFmpeg command and filter graph construction, multi-stream composition with layout presets, audio mixing and transition builders, batch progress aggregation, preview filter simplification and quality selection, and input sanitization. All types and functions are exposed to Python via PyO3 bindings with hand-maintained `.pyi` type stubs.

## Responsibilities

- Provide frame-accurate timeline primitives (Position, Duration, FrameRate, TimeRange) using integer frame counts to avoid floating-point precision errors
- Validate video clips against structural rules (non-empty source path, out_point > in_point) and temporal bounds (in/out points within source duration)
- Build type-safe FFmpeg argument arrays and filter graph strings via a builder pattern without shell escaping hazards
- Supply video and audio effect builders: speed control, text overlay, volume, fade, audio mix, cross-fade, audio ducking, transitions
- Provide layout presets (PIP variants, side-by-side, top-bottom, grid) with normalized coordinate computation and pixel conversion
- Build composition graphs for multi-stream video layouts by combining clip validation, layout resolution, and filter graph assembly
- Compute aggregated batch render progress from individual job statuses
- Simplify filter graphs for preview playback by removing expensive filters at lower quality levels, estimate filter computational cost, and select appropriate preview quality
- Sanitize and validate user-supplied text, paths, codecs, presets, and numeric parameters before use in FFmpeg commands
- Expose all types and functions to Python via a single `_core` PyO3 module with custom exception types

## Interfaces

### Provided Interfaces

**Timeline Types**
- `FrameRate` — Rational frame rate (numerator/denominator); factory methods `fps_23_976()` through `fps_60()`
- `Position` — Frame count-based timeline position; `from_secs(seconds, fps)`, `as_secs(fps)`, comparison operators
- `Duration` — Frame count-based duration; `between_positions(start, end)`, `end_pos(start)`, comparison operators
- `TimeRange` — Half-open interval [start, end); `overlaps()`, `adjacent()`, `gap()`, `overlap()`, `union()`, `difference()`
- `find_gaps(ranges) -> list[TimeRange]`
- `merge_ranges(ranges) -> list[TimeRange]`
- `total_coverage(ranges) -> Duration`

**Clip Validation**
- `Clip(source_path, in_point, out_point, source_duration) -> Clip`
- `ClipValidationError` — Structured error with `field`, `message`, `actual`, `expected`
- `validate_clip(clip) -> list[ClipValidationError]`
- `validate_clips(clips) -> list[tuple[int, ClipValidationError]]` — Batch validation with clip index

**FFmpeg Command Builder**
- `FFmpegCommand` — Fluent builder: `.input()`, `.output()`, `.video_codec()`, `.audio_codec()`, `.crf()`, `.preset()`, `.filter_complex()`, `.map()`, `.build() -> list[str]`
- `Filter`, `FilterChain`, `FilterGraph` — Filter graph assembly types
- `scale_filter(width, height) -> Filter`
- `concat_filter(video_count, audio_count) -> Filter`

**Video Effect Builders**
- `SpeedControl(speed_multiplier)` — `setpts`/`atempo` filter generation
- `DrawtextBuilder(text, x, y, fontsize)` — `drawtext` filter with optional font, color, border

**Audio Builders**
- `VolumeBuilder(volume)` — `volume` filter
- `AfadeBuilder(fade_type)` — `afade` filter with duration
- `AmixBuilder(input_count)` — `amix` filter with per-input weights
- `DuckingPattern(target_db, attack_ms, release_ms)` — `sidechaincompress` ducking filter
- `TrackAudioConfig(track_index, volume, pan)` — Per-track configuration
- `AudioMixSpec(tracks, output_channels, output_sample_rate)` — Complete mix specification

**Transition Builders**
- `TransitionType` — Enum: `Fade`, `Xfade`, `Acrossfade`
- `FadeBuilder(fade_type)` — `fade` filter
- `XfadeBuilder(transition_type)` — `xfade` filter
- `AcrossfadeBuilder()` — `acrossfade` filter

**Layout Types**
- `LayoutPosition(x, y, width, height, z_index)` — Normalized 0.0–1.0 coordinates; `to_pixels(width, height) -> tuple[int,int,int,int]`; `validate()`
- `LayoutPreset` — Enum variants: `PipTopLeft`, `PipTopRight`, `PipBottomLeft`, `PipBottomRight`, `SideBySide`, `TopBottom`, `Grid2x2`; `positions(input_count) -> list[LayoutPosition]`

**Composition**
- `build_composition_graph(clips, preset, output_width, output_height, fps) -> CompositionGraph`
- `build_overlay_filter(source_input, overlay_input, position, output_width, output_height) -> Filter`
- `calculate_composition_positions(clips, preset) -> list[AdjustedClipPosition]`
- `calculate_timeline_duration(clips, transitions) -> float`
- `build_composition_graph()` — Returns `CompositionGraph` with `.to_filter_string()`

**Batch Progress**
- `BatchJobStatus` — Factory methods: `pending()`, `in_progress(progress)`, `completed()`, `failed()`; `.progress() -> float`
- `BatchProgress` — `total_jobs`, `completed_jobs`, `failed_jobs`, `overall_progress`
- `calculate_batch_progress(jobs: list[BatchJobStatus]) -> BatchProgress`

**Preview Quality**
- `PreviewQuality` — Enum: `Draft`, `Medium`, `High`
- `is_expensive_filter(name: str) -> bool` — Classify filter by computational cost
- `simplify_filter_chain(chain: FilterChain, quality: PreviewQuality) -> FilterChain` — Remove expensive filters at Draft/Medium
- `simplify_filter_graph(graph: FilterGraph, quality: PreviewQuality) -> FilterGraph` — Remove expensive filters from full graph
- `estimate_filter_cost(graph: FilterGraph) -> float` — Sigmoid-normalized cost in [0.0, 1.0]
- `select_preview_quality(cost: float) -> PreviewQuality` — Auto-select quality (High: <0.3, Medium: 0.3–0.7, Draft: >0.7)
- `inject_preview_scale(graph: FilterGraph, width: int, height: int) -> FilterGraph` — Append scale filter for resolution control

**Sanitization**
- `escape_filter_text(text) -> str` — Escapes FFmpeg special chars: `\`, `'`, `:`, `[`, `]`, `;`
- `validate_path(path) -> None` — Rejects empty or null-byte paths
- `validate_volume(volume) -> float` — Range 0.0–10.0
- `validate_speed(speed) -> float` — Range 0.25–4.0
- `validate_crf(crf) -> int` — Range 0–51
- `validate_video_codec(codec) -> str` — Whitelist: libx264, libx265, libvpx, libvpx-vp9, libaom-av1, copy
- `validate_audio_codec(codec) -> str` — Whitelist: aac, libopus, libmp3lame, copy
- `validate_preset(preset) -> str` — Whitelist of FFmpeg encoding presets

**Utility**
- `health_check() -> str` — Returns "stoat_ferret_core OK"

**Custom Python Exceptions**
- `ValidationError` — Clip or parameter validation failures
- `CommandError` — FFmpeg command building errors
- `SanitizationError` — Input sanitization failures
- `LayoutError` — Layout coordinate validation failures

### Required Interfaces

None — the Rust crate has no runtime dependencies on other application components. It is a self-contained native library.

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Crate Root | `rust/stoat_ferret_core/src/lib.rs` | PyO3 module registration, custom exception types, `health_check()`, stub generation entry point |
| Timeline | `rust/stoat_ferret_core/src/timeline/` | `FrameRate`, `Position`, `Duration`, `TimeRange`; integer frame arithmetic; gap/merge/coverage functions |
| Clip | `rust/stoat_ferret_core/src/clip/` | `Clip` struct; `ClipValidationError`; `validate_clip()`; `validate_clips()` batch validation |
| FFmpeg | `rust/stoat_ferret_core/src/ffmpeg/` | `FFmpegCommand` builder; `Filter`, `FilterChain`, `FilterGraph`; all effect builders (speed, drawtext, volume, fade, amix, ducking, transitions) |
| Layout | `rust/stoat_ferret_core/src/layout/` | `LayoutPosition` with pixel conversion; `LayoutPreset` enum with position factories; `LayoutError` |
| Compose | `rust/stoat_ferret_core/src/compose/` | `build_composition_graph()`; overlay and scale filter helpers; composition timeline builders |
| Batch | `rust/stoat_ferret_core/src/batch.rs` | `BatchJobStatus`; `BatchProgress`; `calculate_batch_progress()` mean-based aggregation |
| Preview | `rust/stoat_ferret_core/src/preview/` | `PreviewQuality` enum; filter classification and simplification; cost estimation (sigmoid); quality auto-selection; scale filter injection |
| Sanitize | `rust/stoat_ferret_core/src/sanitize/` | `escape_filter_text()`; `validate_path()`; numeric bounds validators; codec and preset whitelists |

## Key Behaviors

**Frame-Accurate Arithmetic:** All timeline calculations use `u64` frame counts. Conversions between frames and seconds use rational arithmetic to preserve exact representation for NTSC frame rates (24000/1001, 30000/1001).

**Incremental Binding Rule:** PyO3 bindings for every Rust type are added in the same feature/commit that introduces the type. Bindings are never deferred. CI verifies that hand-maintained `.pyi` stubs cover all types from the generated baseline.

**`py_` Naming Convention:** PyO3 method implementations use a `py_` prefix internally (e.g., `fn py_calculate`), and `#[pyo3(name = "...")]` exposes a clean name to Python (e.g., `calculate`). This distinguishes Python-API methods from internal Rust methods.

**Resolution-Independent Layouts:** All `LayoutPosition` coordinates are stored as normalized 0.0–1.0 values. Pixel conversion via `to_pixels(output_width, output_height)` uses `round()` and is deferred to render time.

**Composition Pipeline:** `build_composition_graph()` validates all clips, resolves preset positions, generates scale filters for each stream, stacks overlay filters by z_index, and returns a complete FFmpeg `filter_complex` string.

**Security via Sanitization:** FFmpeg filter text from users is escaped via `escape_filter_text()`. Codec and preset selections are validated against whitelists rather than escaped, preventing injection through enumerated options.

## Inter-Component Relationships

```
API Gateway
    |-- calls (clip validation) --> Rust Core
    |-- calls (layout/composition) --> Rust Core
    |-- calls (audio mix filters) --> Rust Core
    |-- calls (batch progress) --> Rust Core
    |-- calls (transition calculation) --> Rust Core

Effects Engine
    |-- calls (all filter builders) --> Rust Core

Data Access (models.py)
    |-- calls validate_clip() --> Rust Core
```

## Version History

| Version | Changes |
|---------|---------|
| v008 | Initial Rust Core with timeline, clip, ffmpeg builders, layout, compose, sanitize |
| v012 | Added `layout.md` and `compose.md` (layout presets, composition graph, overlay builders) |
| v014 | Added `batch.md` (batch progress aggregation) |
| v015 | Added `AudioMixSpec`, `TrackAudioConfig`, `VolumeBuilder` bindings for audio mix support |
| v016 | Added transition calculation helpers: `calculate_composition_positions()`, `calculate_timeline_duration()`, `CompositionClip`, `TransitionSpec` |
| v027 | Added preview module: `PreviewQuality` enum, filter classification and simplification, cost estimation, quality auto-selection, scale filter injection |
