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
- `audio.rs` - Audio filter builders (`VolumeBuilder`, `AfadeBuilder`, `AmixBuilder`, `DuckingPattern`)
- `speed.rs` - Speed control builder (`SpeedControl`) for video/audio speed adjustment
- `transitions.rs` - Video/audio transition builders (`FadeBuilder`, `XfadeBuilder`, `TransitionType`)
- `drawtext.rs` - Text overlay builder (`DrawtextBuilder`) with positioning presets and alpha fading
- `expression.rs` - FFmpeg expression tree builder (`Expr`, `Variable`, `BinaryOp`, `FuncName`)

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

### Key Methods

- `FFmpegCommand::new()`, `.input()`, `.output()`, `.seek()`, `.filter_complex()`, `.build()`
- `Filter::new()`, `.param()` - Builder for single filters
- `FilterChain::input()`, `.filter()`, `.output()` - Sequential filter composition
- `FilterGraph::chain()`, `.validate()` - Graph composition with validation
- `SpeedControl::new()`, `.setpts_filter()`, `.atempo_filters()` - Speed adjustment
- `DrawtextBuilder::new()`, `.position()`, `.alpha_fade()`, `.build()` - Text overlays
- `Expr::constant()`, `.var()`, `.between()`, `.if_then_else()` - Expression construction

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
```

## Notes

- **Fluent builder pattern**: All builders support method chaining
- **PyO3 bindings**: Complete Python FFI via `#[pyclass]` and `#[pymethods]`
- **No shell escaping**: `Vec<String>` args for safe `std::process::Command` use
- **Validation at build time**: Commands and filters validate on `.build()`
- **Expression precedence**: Binary operations respect math precedence
- **Speed decomposition**: atempo auto-chains speeds outside [0.5, 2.0]
- **Text escaping**: Drawtext escapes special chars and `%` as `%%`
- **Extensive testing**: Property-based tests via proptest
