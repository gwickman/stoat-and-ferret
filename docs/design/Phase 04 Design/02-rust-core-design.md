# Phase 4: Rust Core Design

## Overview

Phase 4 extends the Rust core (`stoat_ferret_core`) with a single focused module: preview filter simplification. Following the established pattern (LRN-011): Rust handles compute-intensive pure functions; Python handles orchestration and business logic.

Per LRN-012, Rust is only used where it provides genuine value. Phase 4's Rust scope is deliberately small - the main value is transforming complex production filter chains into lighter preview variants, which involves string-heavy filter manipulation where Rust excels.

## New Rust Module

### Module: `preview` (new)

Preview filter simplification - transforms production-quality filter graphs into lighter variants suitable for real-time preview playback.

```rust
// rust/stoat_ferret_core/src/preview/mod.rs
pub mod simplify;

// rust/stoat_ferret_core/src/preview/simplify.rs

use crate::ffmpeg::filter::{Filter, FilterChain, FilterGraph};

/// Preview quality level controlling simplification aggressiveness.
#[pyclass]
#[derive(Clone, Debug)]
pub enum PreviewQuality {
    /// Minimal simplification - close to production quality
    High,
    /// Moderate simplification - good balance of speed and fidelity
    Medium,
    /// Aggressive simplification - fastest preview, lowest fidelity
    Draft,
}

/// Simplify a FilterGraph for preview playback.
///
/// Transformations applied based on quality level:
/// - Draft: Remove complex text animations, reduce overlay count,
///   skip audio effects, simplify transitions to cuts
/// - Medium: Simplify text animations to static, reduce transition
///   quality, skip audio normalization
/// - High: Only remove computationally expensive filters
///   (heavy blur, complex color grading)
///
/// Pure function - deterministic, no side effects.
#[pyfunction]
pub fn simplify_filter_graph(
    graph: &FilterGraph,
    quality: PreviewQuality,
) -> FilterGraph {
    // Returns a new FilterGraph with simplified filters
    // Original graph is not modified
    ...
}

/// Simplify a single FilterChain for preview.
/// Used when previewing a single clip's effects.
#[pyfunction]
pub fn simplify_filter_chain(
    chain: &FilterChain,
    quality: PreviewQuality,
) -> FilterChain {
    ...
}

/// Check if a filter is computationally expensive.
/// Used by simplification logic and metrics.
#[pyfunction]
pub fn is_expensive_filter(filter_name: &str) -> bool {
    matches!(filter_name,
        "hue" | "eq" | "colorbalance" | "unsharp" |
        "gblur" | "boxblur" | "smartblur" |
        "atadenoise" | "nlmeans" |
        "perspective" | "lenscorrection"
    )
}

/// Estimate the computational cost of a filter graph.
/// Returns a relative cost score (0.0 = trivial, 1.0 = very expensive).
/// Used for preview quality auto-selection.
#[pyfunction]
pub fn estimate_filter_cost(graph: &FilterGraph) -> f64 {
    ...
}
```

### Simplification Rules

| Filter Type | Draft | Medium | High |
|-------------|-------|--------|------|
| `drawtext` with alpha animation | Remove animation, static text | Simplify animation | Keep as-is |
| `xfade` transitions | Replace with cut | Reduce to simple fade | Keep as-is |
| `overlay` (PIP) | Keep (required for layout) | Keep | Keep |
| `gblur`/`boxblur` | Remove | Reduce radius | Keep |
| `eq`/`colorbalance` | Remove | Keep | Keep |
| `amix` (audio) | Skip entirely | Simplified mix | Keep |
| `afade` (audio) | Skip | Keep | Keep |
| `scale` | Force preview resolution | Force preview resolution | Keep |

### Scale Injection for Preview Resolution

All preview filter chains get a resolution-limiting scale filter injected:

```rust
/// Inject scale filter to limit preview output resolution.
/// Appended to the filter graph output.
#[pyfunction]
pub fn inject_preview_scale(
    graph: &FilterGraph,
    max_width: u32,
    max_height: u32,
) -> FilterGraph {
    // Adds scale=w=min(iw,{max_width}):h=min(ih,{max_height}):
    //   force_original_aspect_ratio=decrease
    // to the final output of the graph
    ...
}
```

## PyO3 Bindings to Add

New bindings in `lib.rs`:

```rust
// Preview module
m.add_class::<PreviewQuality>()?;
m.add_function(wrap_pyfunction!(simplify_filter_graph, m)?)?;
m.add_function(wrap_pyfunction!(simplify_filter_chain, m)?)?;
m.add_function(wrap_pyfunction!(is_expensive_filter, m)?)?;
m.add_function(wrap_pyfunction!(estimate_filter_cost, m)?)?;
m.add_function(wrap_pyfunction!(inject_preview_scale, m)?)?;
```

## Property-Based Tests

```rust
proptest! {
    #[test]
    fn simplification_never_panics(
        filter_count in 1usize..20,
        quality in prop::sample::select(vec![
            PreviewQuality::Draft,
            PreviewQuality::Medium,
            PreviewQuality::High,
        ]),
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let _ = simplify_filter_graph(&graph, quality);
    }

    #[test]
    fn simplified_graph_has_fewer_or_equal_filters(
        filter_count in 1usize..20,
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let simplified = simplify_filter_graph(&graph, PreviewQuality::Draft);
        assert!(simplified.filter_count() <= graph.filter_count());
    }

    #[test]
    fn cost_estimation_bounded(
        filter_count in 1usize..20,
    ) {
        let graph = generate_random_filter_graph(filter_count);
        let cost = estimate_filter_cost(&graph);
        assert!(cost >= 0.0 && cost <= 1.0);
    }
}
```

## File Structure

```
rust/stoat_ferret_core/src/
├── lib.rs                    # add new bindings
├── preview/                  # NEW
│   ├── mod.rs
│   └── simplify.rs           # filter simplification + cost estimation
├── layout/                   # existing (no changes)
├── compose/                  # existing (no changes)
├── ffmpeg/                   # existing (no changes)
├── timeline/                 # existing (no changes)
├── clip/                     # existing (no changes)
└── sanitize/                 # existing (no changes)
```

## Design Decisions

1. **Single module, focused scope**: Only filter simplification in Rust. HLS generation, proxy management, waveform creation, and cache management are all Python/FFmpeg orchestration - no benefit from Rust.

2. **Non-destructive simplification**: `simplify_filter_graph` returns a new graph, never modifies the input. The production graph is always preserved for final render.

3. **Quality-tiered simplification**: Three levels allow the frontend to auto-select based on system capability, or let users choose explicitly.

4. **Cost estimation enables auto-quality**: `estimate_filter_cost` lets Python decide preview quality automatically based on timeline complexity.

5. **Reuses existing FilterGraph type**: Simplified graphs are the same `FilterGraph` type from Phase 2, so they flow through the same FFmpeg command builder pipeline.
