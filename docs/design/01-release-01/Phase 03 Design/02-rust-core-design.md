# Phase 3: Rust Core Design

## Overview

Phase 3 extends the Rust core (`stoat_ferret_core`) with layout calculations, multi-track timeline composition, and parallelism support. Following the established pattern (LRN-011): Rust handles compute-intensive pure functions; Python handles orchestration and business logic.

Per LRN-012, Rust is only used where it provides genuine value (string-heavy filter generation, complex math). Simple operations stay in Python.

## New Rust Modules

### Module: `layout` (new)

Layout math for PIP, split-screen, and custom multi-stream compositions.

```rust
// rust/stoat_ferret_core/src/layout/mod.rs
pub mod position;
pub mod preset;

// rust/stoat_ferret_core/src/layout/position.rs

#[pyclass]
#[derive(Clone, Debug)]
pub struct LayoutPosition {
    #[pyo3(get, set)]
    pub x: f64,       // normalized 0.0-1.0
    #[pyo3(get, set)]
    pub y: f64,
    #[pyo3(get, set)]
    pub width: f64,
    #[pyo3(get, set)]
    pub height: f64,
    #[pyo3(get, set)]
    pub z_index: i32,
}

#[pymethods]
impl LayoutPosition {
    #[new]
    pub fn new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self { ... }

    /// Convert normalized position to pixel coordinates
    pub fn to_pixels(&self, output_width: u32, output_height: u32) -> (i32, i32, u32, u32) { ... }

    /// Validate position is within bounds
    pub fn validate(&self) -> Result<(), LayoutError> { ... }
}

// rust/stoat_ferret_core/src/layout/preset.rs

#[pyclass]
#[derive(Clone, Debug)]
pub enum LayoutPreset {
    PipTopLeft,
    PipTopRight,
    PipBottomLeft,
    PipBottomRight,
    SideBySide,
    TopBottom,
    Grid2x2,
}

#[pymethods]
impl LayoutPreset {
    /// Generate positions for N inputs using this preset
    pub fn positions(&self, count: usize) -> Vec<LayoutPosition> { ... }
}
```

### Module: `compose` (new)

Multi-clip composition and filter graph generation.

```rust
// rust/stoat_ferret_core/src/compose/mod.rs
pub mod timeline;
pub mod overlay;
pub mod graph;

// rust/stoat_ferret_core/src/compose/timeline.rs

#[pyclass]
#[derive(Clone, Debug)]
pub struct CompositionClip {
    #[pyo3(get)]
    pub input_index: usize,
    #[pyo3(get)]
    pub timeline_start: f64,
    #[pyo3(get)]
    pub timeline_end: f64,
    #[pyo3(get)]
    pub track_index: usize,
    #[pyo3(get)]
    pub z_index: i32,
}

/// Calculate clip positions with transition overlaps.
/// Pure function — deterministic, no side effects.
#[pyfunction]
pub fn calculate_composition_positions(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
) -> Vec<CompositionClip> { ... }

/// Calculate total timeline duration accounting for transitions.
#[pyfunction]
pub fn calculate_timeline_duration(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
) -> f64 { ... }

// rust/stoat_ferret_core/src/compose/overlay.rs

/// Build overlay filter for PIP composition.
/// Pure function generating FFmpeg overlay filter string.
#[pyfunction]
pub fn build_overlay_filter(
    position: &LayoutPosition,
    output_width: u32,
    output_height: u32,
    start_time: f64,
    end_time: f64,
) -> String { ... }

/// Build scale filter for resizing input to layout position.
#[pyfunction]
pub fn build_scale_for_layout(
    position: &LayoutPosition,
    output_width: u32,
    output_height: u32,
    preserve_aspect: bool,
) -> String { ... }

// rust/stoat_ferret_core/src/compose/graph.rs

/// Build a complete FilterGraph for multi-clip composition.
/// This is the primary composition entry point.
#[pyfunction]
pub fn build_composition_graph(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
    layout: Option<LayoutSpec>,
    audio_mix: Option<AudioMixSpec>,
    output_width: u32,
    output_height: u32,
) -> FilterGraph { ... }
```

### Module: `audio` (extend existing)

The existing `ffmpeg/audio.rs` module has `AmixBuilder`, `VolumeBuilder`, `AfadeBuilder`, and `DuckingPattern`. Phase 3 adds multi-track coordination.

```rust
// rust/stoat_ferret_core/src/ffmpeg/audio.rs (additions)

#[pyclass]
#[derive(Clone, Debug)]
pub struct AudioMixSpec {
    #[pyo3(get, set)]
    pub track_volumes: Vec<f64>,
    #[pyo3(get, set)]
    pub fade_ins: Vec<f64>,
    #[pyo3(get, set)]
    pub fade_outs: Vec<f64>,
    #[pyo3(get, set)]
    pub master_volume: f64,
    #[pyo3(get, set)]
    pub normalize: bool,
}

#[pymethods]
impl AudioMixSpec {
    #[new]
    pub fn new(track_count: usize) -> Self { ... }

    /// Build complete audio filter chain for all tracks.
    /// Uses existing AmixBuilder, VolumeBuilder, AfadeBuilder internally.
    pub fn build_filter_chain(&self) -> FilterChain { ... }

    /// Validate all volume/fade values are in acceptable ranges.
    pub fn validate(&self) -> Result<(), AudioMixError> { ... }
}
```

### Module: `batch` (new)

Batch processing progress calculation (pure math, no I/O).

```rust
// rust/stoat_ferret_core/src/batch.rs

#[pyclass]
#[derive(Clone, Debug)]
pub struct BatchProgress {
    #[pyo3(get)]
    pub total_jobs: usize,
    #[pyo3(get)]
    pub completed_jobs: usize,
    #[pyo3(get)]
    pub failed_jobs: usize,
    #[pyo3(get)]
    pub overall_progress: f64,  // 0.0-1.0
}

/// Calculate batch progress from individual job progresses.
#[pyfunction]
pub fn calculate_batch_progress(
    job_progresses: Vec<f64>,
    job_statuses: Vec<String>,
) -> BatchProgress { ... }
```

## PyO3 Bindings to Add

New bindings in `lib.rs`:

```rust
// Layout module
m.add_class::<LayoutPosition>()?;
m.add_class::<LayoutPreset>()?;

// Compose module
m.add_class::<CompositionClip>()?;
m.add_class::<AudioMixSpec>()?;
m.add_class::<BatchProgress>()?;
m.add_function(wrap_pyfunction!(calculate_composition_positions, m)?)?;
m.add_function(wrap_pyfunction!(calculate_timeline_duration, m)?)?;
m.add_function(wrap_pyfunction!(build_overlay_filter, m)?)?;
m.add_function(wrap_pyfunction!(build_scale_for_layout, m)?)?;
m.add_function(wrap_pyfunction!(build_composition_graph, m)?)?;
m.add_function(wrap_pyfunction!(calculate_batch_progress, m)?)?;
```

## Parallelism Approach

Phase 3 introduces Rayon for CPU-parallel layout calculations when composing many streams:

```rust
use rayon::prelude::*;

/// Build scale filters for all layout positions in parallel.
pub fn build_all_scale_filters(
    positions: &[LayoutPosition],
    output_width: u32,
    output_height: u32,
) -> Vec<String> {
    positions.par_iter()
        .map(|pos| build_scale_for_layout(pos, output_width, output_height, true))
        .collect()
}
```

Rayon is only used where parallelism provides measurable benefit (>4 concurrent streams). For typical 2-4 stream compositions, sequential execution is sufficient. Follow LRN-012: benchmark before assuming Rust parallelism helps.

## Dependency Additions

```toml
# rust/stoat_ferret_core/Cargo.toml
[dependencies]
rayon = "1.8"   # parallel iteration (used sparingly)
```

## File Structure

```
rust/stoat_ferret_core/src/
├── lib.rs                    # add new bindings
├── layout/                   # NEW
│   ├── mod.rs
│   ├── position.rs           # LayoutPosition + pixel math
│   └── preset.rs             # LayoutPreset definitions
├── compose/                  # NEW
│   ├── mod.rs
│   ├── timeline.rs           # multi-clip position calculation
│   ├── overlay.rs            # overlay/scale filter generation
│   └── graph.rs              # complete FilterGraph builder
├── batch.rs                  # NEW - batch progress math
├── ffmpeg/
│   ├── audio.rs              # EXTEND with AudioMixSpec
│   ├── transitions.rs        # existing (no changes needed)
│   ├── ...                   # existing modules unchanged
├── timeline/                 # existing (no changes needed)
├── clip/                     # existing (no changes needed)
└── sanitize/                 # existing (no changes needed)
```

## Design Decisions

1. **Composition graph builds on existing FilterGraph**: The `build_composition_graph` function produces a `FilterGraph` (existing type from Phase 2's `ffmpeg/filter.rs`), not a new type. This reuses the validated filter graph infrastructure.

2. **Layout positions are normalized (0.0-1.0)**: Resolution-independent positioning simplifies preset definitions and allows the same layout to work at any output resolution.

3. **AudioMixSpec wraps existing builders**: Rather than replacing `AmixBuilder`/`VolumeBuilder`/`AfadeBuilder`, the new `AudioMixSpec` composes them. This follows LRN-065 (preserve internal implementations).

4. **Minimal Rayon usage**: Only for parallel scale filter generation with >4 streams. Sequential execution for typical use cases per LRN-012 findings.
