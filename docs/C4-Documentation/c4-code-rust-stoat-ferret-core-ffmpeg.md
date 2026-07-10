# C4 Code Level: FFmpeg Command Builder Module

## Overview

- **Name**: FFmpeg Command Building and Filtering
- **Description**: Type-safe Rust builders for constructing FFmpeg commands and complex filter graphs without shell escaping.
- **Location**: `rust/stoat_ferret_core/src/ffmpeg`
- **Language**: Rust
- **Purpose**: Provides domain-specific abstractions for FFmpeg command arguments, filter chains, speed control, text overlays, audio mixing, and video transitions—with full PyO3 bindings for Python access.
- **Parent Component**: [Rust Core Engine](./c4-component-rust-core-engine.md)

## Code Elements

### Modules

- `mod.rs` - Module root with FFmpeg exports and integration tests
- `command.rs` - FFmpeg command builder (`FFmpegCommand`) for argument construction
- `filter.rs` - Filter chain builder (`Filter`, `FilterChain`, `FilterGraph`) for complex filtergraphs
- `audio.rs` - Audio filter builders (`VolumeBuilder`, `AfadeBuilder`, `AmixBuilder`, `DuckingPattern`, `SubBassBuilder`)
- `spatial.rs` - Spatial audio builders (`PanBuilder`, `ConvolutionReverbBuilder`); new module added v079 PRs #570–#577
- `speed.rs` - Speed control builder (`SpeedControl`) for video/audio speed adjustment
- `transitions.rs` - Video/audio transition builders (`FadeBuilder`, `XfadeBuilder`, `TransitionType`)
- `drawtext.rs` - Text overlay builder (`DrawtextBuilder`) with positioning presets and alpha fading
- `expression.rs` - FFmpeg expression tree builder (`Expr`, `Variable`, `BinaryOp`, `FuncName`)
- `voice_repair.rs` - Voice repair and pitch/time builders (`PitchShiftBuilder`, `TimeStretchBuilder`)

### Key Structs

- `FFmpegCommand` - Builder for FFmpeg argument arrays; validates inputs, outputs, CRF range [0-51]
- `Filter` - Single filter with name and key-value parameters
- `FilterChain` - Sequence of filters with input/output labels
- `FilterGraph` - Multiple filter chains with cycle/duplicate validation
- `SpeedControl` - Speed multiplier [0.25, 4.0] with setpts (video) and atempo chain generation
- `VolumeBuilder` - Audio volume (linear or dB mode)
- `AfadeBuilder` - Audio fade in/out with 11 curve types
- `AmixBuilder` - Audio mixing for 2-32 inputs with duration/weight modes
- `FadeBuilder` - Video fade in/out with color and alpha
- `XfadeBuilder` - Video crossfade with 59 transition types
- `DrawtextBuilder` - Text overlay with position presets, shadow, box background, alpha animation
- `Expr` - Expression tree for FFmpeg filter expressions (const, var, binary ops, functions)
- `PanBuilder` - Spatial audio stereo pan with optional automation envelope (`ffmpeg/spatial.rs:29`)
- `ConvolutionReverbBuilder` - Convolution reverb via impulse response file; produces `afir` filter (`ffmpeg/spatial.rs:80`)
- `SubBassBuilder` - Sub-bass isolation filter chain; cutoff frequency with optional boost (`ffmpeg/audio.rs:1134`)
- `PitchShiftBuilder` - Pitch shift via rubberband filter; adjusts pitch without changing duration (`ffmpeg/voice_repair.rs:1417`)
- `TimeStretchBuilder` - Time-stretch builder; changes duration without altering pitch (`ffmpeg/voice_repair.rs:971`)

### Key Methods

- `FFmpegCommand::new()`, `.input()`, `.output()`, `.seek()`, `.filter_complex()`, `.build()`
- `Filter::new()`, `.param()` - Builder for single filters
- `FilterChain::input()`, `.filter()`, `.output()` - Sequential filter composition
- `FilterGraph::chain()`, `.validate()` - Graph composition with validation
- `SpeedControl::new()`, `.setpts_filter()`, `.atempo_filters()` - Speed adjustment
- `DrawtextBuilder::new()`, `.position()`, `.alpha_fade()`, `.build()` - Text overlays
- `Expr::constant()`, `.var()`, `.between()`, `.if_then_else()` - Expression construction
- `PanBuilder::py_new(position: f32)`, `.with_automation()`, `.build()` - Spatial pan filter
- `ConvolutionReverbBuilder::py_new(ir_name, mix)`, `.build()`, `.ir_name()` - Convolution reverb filter
- `SubBassBuilder::py_new(cutoff_hz: f64)`, `.with_level_db()`, `.build()` - Sub-bass filter chain
- `PitchShiftBuilder::py_new(semitones: f64)`, `.with_formant()`, `.with_quality()`, `.build()` - Pitch shift filter chain
- `TimeStretchBuilder::py_new(factor: f64, mode: str)`, `.build()` - Time-stretch filter chain

### Error Types

- `CommandError` - No inputs/outputs, empty path, invalid CRF
- `GraphValidationError` - Unconnected pad, cycle detected, duplicate label
- `ExprError` - Function arity mismatch

## Dependencies

### Internal
- `crate::sanitize` - Speed/volume validation
- `pyo3` - Python/Rust interop with PyO3 FFI
- `pyo3_stub_gen` - Automatic stub generation

### External
- `proptest` (dev) - Property-based testing

## Relationships

```mermaid
classDiagram
    class FFmpegCommand {
        +inputs: Vec~InputSpec~
        +outputs: Vec~OutputSpec~
        +filter_complex: Option~String~
        +build() Result~Vec~String~~
    }
    class Filter {
        +name: String
        +params: Vec~(String, String)~
        +new() Filter
        +param() Filter
    }
    class FilterChain {
        +inputs: Vec~String~
        +filters: Vec~Filter~
        +outputs: Vec~String~
    }
    class FilterGraph {
        +chains: Vec~FilterChain~
        +validate() Result
    }
    class SpeedControl {
        +speed_factor: f64
        +setpts_filter() Filter
        +atempo_filters() Vec~Filter~
    }
    class VolumeBuilder {
        +volume_str: String
        +build() Filter
    }
    class AfadeBuilder {
        +fade_type: String
        +duration: f64
        +build() Filter
    }
    class AmixBuilder {
        +inputs: usize
        +build() Filter
    }
    class FadeBuilder {
        +fade_type: String
        +duration: f64
        +build() Filter
    }
    class XfadeBuilder {
        +transition: TransitionType
        +duration: f64
        +build() Filter
    }
    enum TransitionType {
        Fade, Fadeblack, Dissolve, Pixelize...
        59 variants
    }
    class DrawtextBuilder {
        +text: String
        +fontsize: u32
        +position: Position
        +alpha_fade() Self
        +build() Filter
    }
    enum Position {
        Absolute, Center, TopLeft
        TopRight, BottomLeft, BottomRight
    }
    class Expr {
        <<enum>>
        Const, Var, BinaryOp, Func
    }
    enum Variable {
        T, N, W, H, TextW, TextH, etc
    }

    FilterGraph *-- FilterChain
    FilterChain *-- Filter
    SpeedControl --> Filter
    VolumeBuilder --> Filter
    AfadeBuilder --> Filter
    AmixBuilder --> Filter
    FadeBuilder --> Filter
    XfadeBuilder --> Filter
    XfadeBuilder --> TransitionType
    DrawtextBuilder --> Filter
    DrawtextBuilder --> Position
    DrawtextBuilder --> Expr
    Expr --> Variable
    PanBuilder --> Filter
    ConvolutionReverbBuilder --> Filter
    class PanBuilder {
        +position: f32
        +with_automation(Automation) Self
        +build() PyResult~Filter~
    }
    class ConvolutionReverbBuilder {
        +ir_name: String
        +mix: f32
        +build() Filter
        +ir_name() String
    }
    class SubBassBuilder {
        +cutoff_hz: f64
        +level_db: f64
        +build() FilterChain
    }
    class PitchShiftBuilder {
        +semitones: f64
        +build() FilterChain
    }
    class TimeStretchBuilder {
        +factor: f64
        +mode: String
        +build() FilterChain
    }
    SubBassBuilder --> FilterChain
    PitchShiftBuilder --> FilterChain
    TimeStretchBuilder --> FilterChain
```

## Module Details

### spatial.rs (new module, v079 PRs #570–#577)

Source: `rust/stoat_ferret_core/src/ffmpeg/spatial.rs` (HEAD `ee6bf44e`)

**PanBuilder** (`ffmpeg/spatial.rs:29`):
Spatial audio pan builder. Positions stereo audio across the left-right field.
- `py_new(position: f32)` — position in [-1.0, 1.0]; -1.0 = full left, 0.0 = center, 1.0 = full right (clamped)
- `with_automation(automation: Automation) -> Self` — enables keyframe-based automation
- `build() -> PyResult<Filter>` — static mode: `pan=stereo|c0=<L>*c0|c1=<R>*c1`; automated mode: `aeval=exprs=...`

**ConvolutionReverbBuilder** (`ffmpeg/spatial.rs:80`):
Convolution reverb using an impulse response (IR) asset file.
- `py_new(ir_name: String, mix: f32)` — `ir_name`: asset identifier; `mix` clamped to [0.0, 1.0]
- `ir_name() -> String` — accessor for IR asset path resolution
- `build() -> Filter` — produces `afir=dry=1:wet=<mix>`

### audio.rs (additions, v079 PR #574)

Source: `rust/stoat_ferret_core/src/ffmpeg/audio.rs` (HEAD `ee6bf44e`)

**SubBassBuilder** (`ffmpeg/audio.rs:1134`):
Sub-bass isolation filter chain builder. Extracts and optionally boosts low-frequency content.
- `py_new(cutoff_hz: f64)` — cutoff frequency in [20.0, 300.0] Hz
- `with_level_db(level_db: f64) -> Self` — boost/cut level in [-20.0, 20.0] dB
- Properties: `cutoff_hz`, `level_db`
- `build() -> FilterChain` — produces `lowpass=f=<cutoff>` optionally followed by `volume` filter

### voice_repair.rs (additions, v079 PRs #575/#577)

Source: `rust/stoat_ferret_core/src/ffmpeg/voice_repair.rs` (HEAD `ee6bf44e`)

**PitchShiftBuilder** (`ffmpeg/voice_repair.rs:1417`):
Pitch shift via rubberband filter. Shifts pitch without changing duration.
- `py_new(semitones: f64)` — range [-24.0, 24.0] semitones
- `with_formant(formant: str) -> Self` — formant handling mode ("preserved" or default)
- `with_quality(quality: str) -> Self` — quality mode ("speedy", etc.)
- `build() -> FilterChain`

**TimeStretchBuilder** (`ffmpeg/voice_repair.rs:971`):
Time-stretch builder. Changes duration without altering pitch.
- `py_new(factor: f64, mode: str)` — factor is stretch ratio; mode: "atempo", "rubberband", or "auto"
- `build() -> FilterChain`

## Notes

- **Fluent builder pattern**: All builders support method chaining
- **PyO3 bindings**: Complete Python FFI via `#[pyclass]` and `#[pymethods]`
- **No shell escaping**: `Vec<String>` args for safe `std::process::Command` use
- **Validation at build time**: Commands and filters validate on `.build()`
- **Expression precedence**: Binary operations respect math precedence
- **Speed decomposition**: atempo auto-chains speeds outside [0.5, 2.0]
- **Text escaping**: Drawtext escapes special chars and `%` as `%%`
- **Extensive testing**: Property-based tests via proptest
