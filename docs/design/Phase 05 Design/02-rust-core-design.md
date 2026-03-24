# Phase 5: Rust Core Design

## Overview

Phase 5 extends the Rust core (`stoat_ferret_core`) with a render coordination module. Following the established pattern (LRN-011): Rust handles compute-intensive pure functions; Python handles orchestration and business logic.

Per LRN-012, Rust is only used where it provides genuine value. Phase 5's Rust scope is larger than Phase 4's (which had one module) because render coordination involves computationally intensive work: building complete FFmpeg filter graphs from timelines, calculating progress/ETA across parallel segments, detecting hardware encoders, and validating render settings. These are all pure-function or system-query operations where Rust excels.

## New Rust Modules

### Module: `render` (new)

Render coordination — transforms a project timeline into executable render plans, detects hardware capabilities, tracks progress, and selects optimal encoders.

### Submodule: `render::plan`

```rust
// rust/stoat_ferret_core/src/render/plan.rs

use crate::compose::CompositionGraph;
use crate::ffmpeg::command::FfmpegCommand;

/// A single segment of a render plan.
#[pyclass]
#[derive(Clone, Debug)]
pub struct RenderSegment {
    #[pyo3(get)]
    pub index: usize,
    #[pyo3(get)]
    pub start_time: f64,
    #[pyo3(get)]
    pub end_time: f64,
    #[pyo3(get)]
    pub filter_graph: String,
    #[pyo3(get)]
    pub input_files: Vec<String>,
    #[pyo3(get)]
    pub estimated_frames: u64,
}

/// Complete render plan for a timeline.
#[pyclass]
#[derive(Clone, Debug)]
pub struct RenderPlan {
    #[pyo3(get)]
    pub segments: Vec<RenderSegment>,
    #[pyo3(get)]
    pub total_frames: u64,
    #[pyo3(get)]
    pub total_duration: f64,
    #[pyo3(get)]
    pub estimated_cost: f64,
    #[pyo3(get)]
    pub requires_concat: bool,
    #[pyo3(get)]
    pub audio_mix_graph: Option<String>,
}

/// Output format for render plan generation.
#[pyclass]
#[derive(Clone, Debug)]
pub enum OutputFormat {
    Mp4,
    Webm,
    ProRes,
    Mov,
}

/// Quality preset controlling encoding parameters.
#[pyclass]
#[derive(Clone, Debug)]
pub enum QualityPreset {
    Draft,
    Medium,
    High,
    Lossless,
}

/// Render output settings.
#[pyclass]
#[derive(Clone, Debug)]
pub struct RenderSettings {
    #[pyo3(get)]
    pub format: OutputFormat,
    #[pyo3(get)]
    pub quality: QualityPreset,
    #[pyo3(get)]
    pub width: u32,
    #[pyo3(get)]
    pub height: u32,
    #[pyo3(get)]
    pub fps: f64,
    #[pyo3(get)]
    pub video_bitrate: Option<u64>,
    #[pyo3(get)]
    pub audio_bitrate: u64,
    #[pyo3(get)]
    pub two_pass: bool,
}

/// Build a complete render plan from a composition graph.
///
/// Analyzes the timeline to determine optimal segment boundaries,
/// builds FFmpeg filter graphs for each segment, and estimates
/// total frame count and computational cost.
///
/// Pure function - deterministic, no side effects.
#[pyfunction]
pub fn build_render_plan(
    graph: &CompositionGraph,
    settings: &RenderSettings,
    segment_duration: f64,  // seconds per segment (0 = no segmentation)
) -> RenderPlan {
    // If segment_duration is 0 or timeline is short, single segment
    // Otherwise, split at clean keyframe boundaries
    ...
}

/// Validate render settings against the composition graph.
/// Returns a list of validation errors (empty = valid).
#[pyfunction]
pub fn validate_render_settings(
    graph: &CompositionGraph,
    settings: &RenderSettings,
) -> Vec<String> {
    // Check: resolution divisible by 2
    // Check: fps within acceptable range
    // Check: format supports requested codec features
    // Check: timeline has content (not empty)
    // Check: all input files referenced in graph
    ...
}
```

### Submodule: `render::encoder`

```rust
// rust/stoat_ferret_core/src/render/encoder.rs

/// Hardware encoder type.
#[pyclass]
#[derive(Clone, Debug, PartialEq)]
pub enum EncoderType {
    Nvenc,
    Vaapi,
    VideoToolbox,
    Qsv,
    Software,
}

/// A detected hardware encoder.
#[pyclass]
#[derive(Clone, Debug)]
pub struct HardwareEncoder {
    #[pyo3(get)]
    pub name: String,           // FFmpeg encoder name
    #[pyo3(get)]
    pub encoder_type: EncoderType,
    #[pyo3(get)]
    pub available: bool,
    #[pyo3(get)]
    pub priority: u32,          // lower = preferred
}

/// Detect available hardware encoders by probing FFmpeg.
///
/// Runs `ffmpeg -encoders` and parses output to find hardware-
/// accelerated encoders. Results should be cached (detection is slow).
///
/// NOT a pure function - performs system I/O. Called once at startup.
#[pyfunction]
pub fn detect_hardware_encoders(ffmpeg_path: &str) -> Vec<HardwareEncoder> {
    // Run ffmpeg -encoders, parse output
    // Check for: h264_nvenc, hevc_nvenc, h264_vaapi, hevc_vaapi,
    //            h264_videotoolbox, hevc_videotoolbox, h264_qsv, hevc_qsv,
    //            prores_videotoolbox, prores_ks
    // Return sorted by priority
    ...
}

/// Select the best encoder for a given output format.
///
/// Walks the fallback chain: HW encoder (by priority) -> SW encoder.
/// Pure function given detected encoders list.
#[pyfunction]
pub fn select_encoder(
    format: &OutputFormat,
    quality: &QualityPreset,
    hw_encoders: &[HardwareEncoder],
) -> HardwareEncoder {
    // Filter hw_encoders by format compatibility
    // Sort by priority (lower first)
    // Return first available, or SW fallback
    ...
}

/// Build encoding parameters for a given encoder and quality preset.
/// Returns a list of FFmpeg CLI arguments for the encoder settings.
///
/// Pure function.
#[pyfunction]
pub fn build_encoding_args(
    encoder: &HardwareEncoder,
    quality: &QualityPreset,
    settings: &RenderSettings,
) -> Vec<String> {
    // Maps quality preset to CRF/CQ values, encoder-specific presets
    // Handles two-pass flags
    // Returns e.g. ["-c:v", "libx264", "-crf", "18", "-preset", "slow"]
    ...
}
```

### Submodule: `render::progress`

```rust
// rust/stoat_ferret_core/src/render/progress.rs

/// Progress state for a render job.
#[pyclass]
#[derive(Clone, Debug)]
pub struct RenderProgress {
    #[pyo3(get)]
    pub progress: f64,          // 0.0 to 1.0
    #[pyo3(get)]
    pub current_frame: u64,
    #[pyo3(get)]
    pub total_frames: u64,
    #[pyo3(get)]
    pub eta_seconds: f64,
    #[pyo3(get)]
    pub fps: f64,               // current render speed
    #[pyo3(get)]
    pub elapsed_seconds: f64,
}

/// Calculate render progress from FFmpeg stderr output.
///
/// Parses FFmpeg progress lines (frame=N fps=N time=HH:MM:SS.ms)
/// and computes overall progress, ETA, and render speed.
///
/// Pure function.
#[pyfunction]
pub fn calculate_progress(
    current_frame: u64,
    total_frames: u64,
    elapsed_seconds: f64,
) -> RenderProgress {
    let progress = if total_frames > 0 {
        (current_frame as f64) / (total_frames as f64)
    } else {
        0.0
    };

    let fps = if elapsed_seconds > 0.0 {
        current_frame as f64 / elapsed_seconds
    } else {
        0.0
    };

    let eta_seconds = if fps > 0.0 && total_frames > current_frame {
        (total_frames - current_frame) as f64 / fps
    } else {
        0.0
    };

    RenderProgress {
        progress: progress.clamp(0.0, 1.0),
        current_frame,
        total_frames,
        eta_seconds,
        fps,
        elapsed_seconds,
    }
}

/// Parse FFmpeg stderr progress line to extract frame count.
///
/// FFmpeg outputs lines like:
///   frame=  150 fps=30.2 q=23.0 size=   1234kB time=00:00:05.00 ...
///
/// Pure function.
#[pyfunction]
pub fn parse_ffmpeg_progress(line: &str) -> Option<(u64, f64)> {
    // Returns (frame_number, time_seconds) if parseable
    ...
}

/// Aggregate progress across multiple parallel segments.
///
/// Used when rendering segments in parallel. Combines per-segment
/// progress into overall job progress.
///
/// Pure function.
#[pyfunction]
pub fn aggregate_segment_progress(
    segment_progress: &[(u64, u64)],  // (completed_frames, total_frames) per segment
    elapsed_seconds: f64,
) -> RenderProgress {
    let total_frames: u64 = segment_progress.iter().map(|(_, t)| t).sum();
    let current_frame: u64 = segment_progress.iter().map(|(c, _)| c).sum();
    calculate_progress(current_frame, total_frames, elapsed_seconds)
}
```

### Submodule: `render::command`

```rust
// rust/stoat_ferret_core/src/render/command.rs

/// Build a complete FFmpeg command for rendering a segment.
///
/// Combines: input files, filter graph, encoder settings, output path.
/// Pure function.
#[pyfunction]
pub fn build_render_command(
    segment: &RenderSegment,
    encoder_args: &[String],
    audio_args: &[String],
    output_path: &str,
    pass_number: Option<u32>,  // None for single-pass, 1 or 2 for two-pass
) -> Vec<String> {
    // Builds complete ffmpeg invocation:
    // ffmpeg -y -i input1.mp4 -i input2.mp4
    //   -filter_complex "..." -map "[v]" -map "[a]"
    //   -c:v libx264 -crf 18 -preset slow
    //   -c:a aac -b:a 192k
    //   output.mp4
    ...
}

/// Build the concat command for joining rendered segments.
///
/// Uses FFmpeg concat demuxer for lossless joining.
/// Pure function.
#[pyfunction]
pub fn build_concat_command(
    segment_paths: &[String],
    output_path: &str,
) -> Vec<String> {
    // ffmpeg -y -f concat -safe 0 -i filelist.txt
    //   -c copy output.mp4
    ...
}

/// Check if a render output file would overwrite an existing file.
/// Returns the conflicting path, or None if safe.
/// NOT pure - checks filesystem.
#[pyfunction]
pub fn check_output_conflict(output_path: &str) -> Option<String> {
    ...
}

/// Estimate output file size based on settings and duration.
/// Used for disk space checks before starting render.
/// Pure function.
#[pyfunction]
pub fn estimate_output_size(
    duration_seconds: f64,
    settings: &RenderSettings,
) -> u64 {
    // Rough estimate: bitrate * duration
    let video_bps = settings.video_bitrate.unwrap_or(8_000_000);
    let audio_bps = settings.audio_bitrate;
    let total_bps = video_bps + audio_bps;
    ((total_bps as f64 * duration_seconds) / 8.0) as u64
}
```

## PyO3 Bindings to Add

New bindings in `lib.rs`:

```rust
// Render module
m.add_class::<RenderSegment>()?;
m.add_class::<RenderPlan>()?;
m.add_class::<OutputFormat>()?;
m.add_class::<QualityPreset>()?;
m.add_class::<RenderSettings>()?;
m.add_class::<HardwareEncoder>()?;
m.add_class::<EncoderType>()?;
m.add_class::<RenderProgress>()?;

m.add_function(wrap_pyfunction!(build_render_plan, m)?)?;
m.add_function(wrap_pyfunction!(validate_render_settings, m)?)?;
m.add_function(wrap_pyfunction!(detect_hardware_encoders, m)?)?;
m.add_function(wrap_pyfunction!(select_encoder, m)?)?;
m.add_function(wrap_pyfunction!(build_encoding_args, m)?)?;
m.add_function(wrap_pyfunction!(calculate_progress, m)?)?;
m.add_function(wrap_pyfunction!(parse_ffmpeg_progress, m)?)?;
m.add_function(wrap_pyfunction!(aggregate_segment_progress, m)?)?;
m.add_function(wrap_pyfunction!(build_render_command, m)?)?;
m.add_function(wrap_pyfunction!(build_concat_command, m)?)?;
m.add_function(wrap_pyfunction!(check_output_conflict, m)?)?;
m.add_function(wrap_pyfunction!(estimate_output_size, m)?)?;
```

## Property-Based Tests

```rust
proptest! {
    #[test]
    fn progress_always_bounded(
        current in 0u64..100_000,
        total in 1u64..100_000,
        elapsed in 0.0f64..10_000.0,
    ) {
        let progress = calculate_progress(current, total, elapsed);
        prop_assert!(progress.progress >= 0.0);
        prop_assert!(progress.progress <= 1.0);
        prop_assert!(progress.eta_seconds >= 0.0);
        prop_assert!(progress.fps >= 0.0);
    }

    #[test]
    fn aggregate_progress_consistent(
        segments in prop::collection::vec((0u64..1000, 100u64..1000), 1..10),
        elapsed in 0.1f64..1000.0,
    ) {
        let progress = aggregate_segment_progress(&segments, elapsed);
        let total: u64 = segments.iter().map(|(_, t)| t).sum();
        let completed: u64 = segments.iter().map(|(c, _)| c).sum();
        prop_assert_eq!(progress.total_frames, total);
        prop_assert_eq!(progress.current_frame, completed);
        prop_assert!(progress.progress >= 0.0);
        prop_assert!(progress.progress <= 1.0);
    }

    #[test]
    fn render_plan_never_panics(
        clip_count in 1usize..20,
        segment_duration in 0.0f64..60.0,
    ) {
        let graph = generate_test_composition_graph(clip_count);
        let settings = RenderSettings {
            format: OutputFormat::Mp4,
            quality: QualityPreset::High,
            width: 1920,
            height: 1080,
            fps: 30.0,
            video_bitrate: Some(8_000_000),
            audio_bitrate: 192_000,
            two_pass: false,
        };
        let _ = build_render_plan(&graph, &settings, segment_duration);
    }

    #[test]
    fn validate_settings_never_panics(
        width in 1u32..8000,
        height in 1u32..5000,
        fps in 0.1f64..200.0,
    ) {
        let graph = generate_test_composition_graph(3);
        let settings = RenderSettings {
            format: OutputFormat::Mp4,
            quality: QualityPreset::High,
            width,
            height,
            fps,
            video_bitrate: Some(8_000_000),
            audio_bitrate: 192_000,
            two_pass: false,
        };
        let _ = validate_render_settings(&graph, &settings);
    }

    #[test]
    fn encoding_args_always_non_empty(
        quality in prop::sample::select(vec![
            QualityPreset::Draft,
            QualityPreset::Medium,
            QualityPreset::High,
            QualityPreset::Lossless,
        ]),
    ) {
        let encoder = HardwareEncoder {
            name: "libx264".to_string(),
            encoder_type: EncoderType::Software,
            available: true,
            priority: 100,
        };
        let settings = RenderSettings {
            format: OutputFormat::Mp4,
            quality: quality.clone(),
            width: 1920, height: 1080, fps: 30.0,
            video_bitrate: Some(8_000_000),
            audio_bitrate: 192_000,
            two_pass: false,
        };
        let args = build_encoding_args(&encoder, &quality, &settings);
        prop_assert!(!args.is_empty());
    }

    #[test]
    fn output_size_estimate_positive(
        duration in 0.1f64..3600.0,
        bitrate in 100_000u64..50_000_000,
    ) {
        let settings = RenderSettings {
            format: OutputFormat::Mp4,
            quality: QualityPreset::High,
            width: 1920, height: 1080, fps: 30.0,
            video_bitrate: Some(bitrate),
            audio_bitrate: 192_000,
            two_pass: false,
        };
        let size = estimate_output_size(duration, &settings);
        prop_assert!(size > 0);
    }
}
```

## File Structure

```
rust/stoat_ferret_core/src/
├── lib.rs                    # add new bindings
├── render/                   # NEW
│   ├── mod.rs
│   ├── plan.rs               # render plan generation from timeline
│   ├── encoder.rs            # hardware detection + encoder selection
│   ├── progress.rs           # progress calculation + FFmpeg output parsing
│   └── command.rs            # FFmpeg render command construction
├── preview/                  # existing (Phase 4, no changes)
├── layout/                   # existing (no changes)
├── compose/                  # existing (no changes)
├── ffmpeg/                   # existing (no changes)
├── timeline/                 # existing (no changes)
├── clip/                     # existing (no changes)
└── sanitize/                 # existing (no changes)
```

## Design Decisions

1. **Four submodules for clear separation**: Plan (what to render), Encoder (how to encode), Progress (tracking), Command (FFmpeg CLI construction). Each is independently testable.

2. **`detect_hardware_encoders` is the only impure function**: It runs FFmpeg to probe the system. All other functions are pure. Detection results are cached in SQLite by Python (see `01-export-data-models.md`).

3. **Reuses existing `CompositionGraph` type**: `build_render_plan` takes the same graph type from Phase 3's composition engine. This ensures render plans reflect exactly what the user composed.

4. **Progress parsing is Rust, not Python**: FFmpeg outputs progress at high frequency. Rust parsing avoids Python GIL overhead and enables efficient aggregation across parallel segments.

5. **Encoder selection is deterministic**: Given the same list of detected encoders and format/quality, `select_encoder` always returns the same result. This makes render behavior reproducible.

6. **`estimate_output_size` enables pre-flight disk checks**: Called before starting render to verify sufficient disk space. Rough estimate is acceptable — the goal is to catch obviously insufficient space.

7. **Segment-based rendering is optional**: `segment_duration=0` produces a single-segment plan. Segmentation is for future parallel rendering — Phase 5 renders sequentially but the data model supports parallelism.

8. **Parallel rendering trigger threshold**: Parallel segment rendering should be activated when timeline duration >= 5 minutes (`render_parallel_min_duration_seconds = 300`). Below this threshold, the overhead of segment splitting at keyframe boundaries, temporary file management, and final concatenation outweighs the speedup. For a 5-minute video, these fixed costs (estimated 2-3 seconds per segment for keyframe alignment and concat I/O) represent <15% of total encode time, making parallelism worthwhile. For shorter videos, modern encoders with frame-level threading typically achieve near-realtime encoding, making segment-based parallelism counterproductive. This threshold is conservative — it can be lowered as implementation matures. See Rationale section below.

### Parallel Rendering Rationale

The 5-minute threshold was chosen based on the following research:

- **Segment overhead is fixed, not proportional**: Each segment incurs startup cost (keyframe alignment, FFmpeg process initialization) and teardown cost (temp file write, concat muxing). With 30-second segments and a 5-minute video (~10 segments), overhead totals ~20-30 seconds — acceptable relative to 3-5 minutes of encode time.
- **Short videos don't benefit**: A 1-minute video at 30fps (1,800 frames) encodes in ~30-60 seconds with modern H.264 threading. Adding segment parallelism overhead of 20-30 seconds would negate most or all of the speedup.
- **Two-pass encoding complicates segmentation**: Per-segment two-pass loses the encoder's ability to do long-term bitrate allocation across the full video, potentially reducing quality. This is acceptable for long videos where speed matters more, but not for short clips.
- **Industry precedent**: Major tools (HandBrake, DaVinci Resolve) rely on frame-level threading rather than segment-based parallelism. Our segment approach is more aggressive and should only activate when clearly beneficial.
- **Conservative default**: Users can override via `render_parallel_min_duration_seconds` configuration. The threshold can be lowered in future versions as the implementation proves stable.
