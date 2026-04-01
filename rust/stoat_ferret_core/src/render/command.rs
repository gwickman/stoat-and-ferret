//! Render command building, concat demuxer generation, output conflict
//! detection, and output size estimation.
//!
//! Generates complete FFmpeg render commands for individual segments,
//! concat demuxer files for multi-segment joins, checks for output path
//! conflicts, and estimates output file sizes based on codec/quality
//! bitrate lookup tables.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::path::Path;

use super::encoder::{build_encoding_args, EncoderInfo, QualityPreset};
use super::plan::{RenderSegment, RenderSettings};

// ---------------------------------------------------------------------------
// Bitrate lookup table (bits per second)
// ---------------------------------------------------------------------------

/// Returns estimated bitrate in bits per second for a given codec and quality
/// preset string.
///
/// Lookup table:
/// - libx264: draft ~2Mbps, standard ~5Mbps, high ~10Mbps
/// - libx265: ~60% of x264 values
/// - libvpx-vp9: ~70% of x264 values
/// - libaom-av1: ~50% of x264 values
///
/// Falls back to x264 values for unknown codecs.
fn lookup_bitrate(codec: &str, quality_preset: &str) -> u64 {
    let base = match quality_preset {
        "draft" => 2_000_000u64,
        "standard" => 5_000_000,
        "high" => 10_000_000,
        _ => 5_000_000, // default to standard
    };

    let multiplier = match codec {
        "libx265" => 0.6,
        "libvpx-vp9" => 0.7,
        "libaom-av1" => 0.5,
        _ => 1.0, // libx264 and others
    };

    (base as f64 * multiplier) as u64
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// A complete FFmpeg render command for a single segment.
///
/// Contains the argument list, output path, and segment index for tracking.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct RenderCommand {
    /// FFmpeg argument list (excludes the `ffmpeg` binary itself).
    pub args: Vec<String>,
    /// Output file path for this segment.
    #[pyo3(get)]
    pub output_path: String,
    /// Zero-based segment index this command renders.
    #[pyo3(get)]
    pub segment_index: usize,
}

#[pymethods]
impl RenderCommand {
    /// Creates a new RenderCommand.
    ///
    /// Args:
    ///     args: FFmpeg argument list.
    ///     output_path: Output file path.
    ///     segment_index: Zero-based segment index.
    #[new]
    pub fn py_new(args: Vec<String>, output_path: String, segment_index: usize) -> Self {
        Self {
            args,
            output_path,
            segment_index,
        }
    }

    /// Returns the FFmpeg argument list.
    #[pyo3(name = "args")]
    fn py_args(&self) -> Vec<String> {
        self.args.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderCommand(segment={}, output={}, args_len={})",
            self.segment_index,
            self.output_path,
            self.args.len()
        )
    }
}

/// Result of a concat demuxer command build.
///
/// Contains the FFmpeg argument list and the concat file content.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct ConcatCommand {
    /// FFmpeg argument list for the concat operation.
    pub args: Vec<String>,
    /// Content of the concat demuxer file (`ffconcat version 1.0` format).
    #[pyo3(get)]
    pub concat_file_content: String,
}

#[pymethods]
impl ConcatCommand {
    /// Creates a new ConcatCommand.
    ///
    /// Args:
    ///     args: FFmpeg argument list.
    ///     concat_file_content: Concat demuxer file content.
    #[new]
    pub fn py_new(args: Vec<String>, concat_file_content: String) -> Self {
        Self {
            args,
            concat_file_content,
        }
    }

    /// Returns the FFmpeg argument list.
    #[pyo3(name = "args")]
    fn py_args(&self) -> Vec<String> {
        self.args.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "ConcatCommand(args_len={}, content_len={})",
            self.args.len(),
            self.concat_file_content.len()
        )
    }
}

// ---------------------------------------------------------------------------
// Command building
// ---------------------------------------------------------------------------

/// Builds a complete FFmpeg render command for a single segment.
///
/// The command includes input file, seek position, duration, encoder-specific
/// arguments, output format, and progress reporting flags.
///
/// Args:
///     segment: The render segment to build a command for.
///     encoder: The selected encoder.
///     quality: The quality preset.
///     settings: Render settings (format, resolution, fps).
///     input_path: Path to the input media file.
///     output_path: Path to write the rendered segment output.
///
/// Returns:
///     A `RenderCommand` with the complete argument list.
pub fn build_render_command(
    segment: &RenderSegment,
    encoder: &EncoderInfo,
    quality: &QualityPreset,
    settings: &RenderSettings,
    input_path: &str,
    output_path: &str,
) -> RenderCommand {
    let mut args: Vec<String> = Vec::new();

    // Input
    args.extend(["-i".to_string(), input_path.to_string()]);

    // Seek to segment start
    args.extend(["-ss".to_string(), format!("{:.6}", segment.timeline_start)]);

    // Duration
    let duration = segment.timeline_end - segment.timeline_start;
    args.extend(["-t".to_string(), format!("{:.6}", duration)]);

    // Encoder-specific args (codec, preset, quality params)
    args.extend(build_encoding_args(encoder, quality));

    // Output format
    args.extend(["-f".to_string(), settings.output_format.clone()]);

    // Resolution
    args.extend([
        "-s".to_string(),
        format!("{}x{}", settings.width, settings.height),
    ]);

    // Frame rate
    args.extend(["-r".to_string(), format!("{}", settings.fps)]);

    // Progress reporting to stdout
    args.extend(["-progress".to_string(), "pipe:1".to_string()]);

    // Overwrite without asking
    args.push("-y".to_string());

    // Output path
    args.push(output_path.to_string());

    RenderCommand {
        args,
        output_path: output_path.to_string(),
        segment_index: segment.index,
    }
}

/// PyO3 binding for `build_render_command`.
#[pyfunction]
#[pyo3(name = "build_render_command")]
pub fn py_build_render_command(
    segment: &RenderSegment,
    encoder: &EncoderInfo,
    quality: &QualityPreset,
    settings: &RenderSettings,
    input_path: &str,
    output_path: &str,
) -> RenderCommand {
    build_render_command(segment, encoder, quality, settings, input_path, output_path)
}

// ---------------------------------------------------------------------------
// Concat demuxer
// ---------------------------------------------------------------------------

/// Builds an FFmpeg concat demuxer command for joining multiple segments.
///
/// Generates `ffconcat version 1.0` file content listing all segment files
/// with forward slashes and `safe=0` for absolute path support.
///
/// Args:
///     segment_outputs: List of segment output file paths.
///     final_output: Path for the final concatenated output.
///     concat_file_path: Path where the concat list file will be written.
///
/// Returns:
///     A `ConcatCommand` with the argument list and file content.
pub fn build_concat_command(
    segment_outputs: &[String],
    final_output: &str,
    concat_file_path: &str,
) -> ConcatCommand {
    // Build ffconcat file content with forward slashes
    let mut content = String::from("ffconcat version 1.0\n");
    for path in segment_outputs {
        let normalized = path.replace('\\', "/");
        content.push_str(&format!("file {normalized}\n"));
    }

    // Build FFmpeg args
    let args = vec![
        "-f".to_string(),
        "concat".to_string(),
        "-safe".to_string(),
        "0".to_string(),
        "-i".to_string(),
        concat_file_path.to_string(),
        "-c".to_string(),
        "copy".to_string(),
        "-y".to_string(),
        final_output.to_string(),
    ];

    ConcatCommand {
        args,
        concat_file_content: content,
    }
}

/// PyO3 binding for `build_concat_command`.
#[pyfunction]
#[pyo3(name = "build_concat_command")]
pub fn py_build_concat_command(
    segment_outputs: Vec<String>,
    final_output: &str,
    concat_file_path: &str,
) -> ConcatCommand {
    build_concat_command(&segment_outputs, final_output, concat_file_path)
}

// ---------------------------------------------------------------------------
// Output conflict check
// ---------------------------------------------------------------------------

/// Checks whether a file already exists at the given output path.
///
/// Args:
///     output_path: Path to check for an existing file.
///
/// Returns:
///     `true` if a file exists at the path, `false` otherwise.
pub fn check_output_conflict(output_path: &str) -> bool {
    Path::new(output_path).exists()
}

/// PyO3 binding for `check_output_conflict`.
#[pyfunction]
#[pyo3(name = "check_output_conflict")]
pub fn py_check_output_conflict(output_path: &str) -> bool {
    check_output_conflict(output_path)
}

// ---------------------------------------------------------------------------
// Output size estimation
// ---------------------------------------------------------------------------

/// Estimates the output file size in bytes.
///
/// Uses a hardcoded bitrate lookup table keyed by (codec, quality_preset)
/// with a 20% safety margin for overestimation.
///
/// Formula: `duration_seconds * bitrate_bps / 8 * 1.2`
///
/// Args:
///     duration_seconds: Total render duration in seconds.
///     codec: Video codec string (e.g., "libx264").
///     quality_preset: Quality preset string ("draft", "standard", "high").
///
/// Returns:
///     Estimated file size in bytes.
pub fn estimate_output_size(duration_seconds: f64, codec: &str, quality_preset: &str) -> u64 {
    let bitrate = lookup_bitrate(codec, quality_preset);
    let bytes = duration_seconds * (bitrate as f64) / 8.0 * 1.2;
    // Ensure non-negative and finite, minimum 1 byte for any positive duration
    if bytes.is_finite() && bytes > 0.0 {
        bytes as u64
    } else if duration_seconds > 0.0 {
        1
    } else {
        0
    }
}

/// PyO3 binding for `estimate_output_size`.
#[pyfunction]
#[pyo3(name = "estimate_output_size")]
pub fn py_estimate_output_size(duration_seconds: f64, codec: &str, quality_preset: &str) -> u64 {
    estimate_output_size(duration_seconds, codec, quality_preset)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::render::encoder::EncoderType;

    // -- Helpers --

    fn test_segment(index: usize, start: f64, end: f64) -> RenderSegment {
        let frame_count = ((end - start) * 30.0) as u64;
        RenderSegment::new(index, start, end, frame_count, frame_count as f64)
    }

    fn test_encoder() -> EncoderInfo {
        EncoderInfo {
            name: "libx264".to_string(),
            codec: "h264".to_string(),
            is_hardware: false,
            encoder_type: EncoderType::Software,
            description: "libx264 H.264".to_string(),
        }
    }

    fn test_settings() -> RenderSettings {
        RenderSettings::new(
            "mp4".to_string(),
            1920,
            1080,
            "libx264".to_string(),
            "medium".to_string(),
            30.0,
        )
    }

    // -- build_render_command tests --

    #[test]
    fn build_render_command_includes_all_required_args() {
        let segment = test_segment(0, 0.0, 5.0);
        let encoder = test_encoder();
        let settings = test_settings();
        let cmd = build_render_command(
            &segment,
            &encoder,
            &QualityPreset::Standard,
            &settings,
            "/input/video.mp4",
            "/output/seg_000.mp4",
        );

        assert!(!cmd.args.is_empty());
        assert_eq!(cmd.output_path, "/output/seg_000.mp4");
        assert_eq!(cmd.segment_index, 0);

        // Input
        assert!(cmd.args.contains(&"-i".to_string()));
        assert!(cmd.args.contains(&"/input/video.mp4".to_string()));

        // Seek and duration
        assert!(cmd.args.contains(&"-ss".to_string()));
        assert!(cmd.args.contains(&"-t".to_string()));

        // Codec args from build_encoding_args
        assert!(cmd.args.contains(&"-c:v".to_string()));
        assert!(cmd.args.contains(&"libx264".to_string()));

        // Output format
        assert!(cmd.args.contains(&"-f".to_string()));
        assert!(cmd.args.contains(&"mp4".to_string()));

        // Resolution
        assert!(cmd.args.contains(&"-s".to_string()));
        assert!(cmd.args.contains(&"1920x1080".to_string()));

        // Frame rate
        assert!(cmd.args.contains(&"-r".to_string()));
        assert!(cmd.args.contains(&"30".to_string()));

        // Progress
        assert!(cmd.args.contains(&"-progress".to_string()));
        assert!(cmd.args.contains(&"pipe:1".to_string()));

        // Overwrite
        assert!(cmd.args.contains(&"-y".to_string()));

        // Output path is last arg
        assert_eq!(cmd.args.last().unwrap(), "/output/seg_000.mp4");
    }

    #[test]
    fn build_render_command_seek_and_duration_values() {
        let segment = test_segment(1, 10.5, 20.0);
        let encoder = test_encoder();
        let settings = test_settings();
        let cmd = build_render_command(
            &segment,
            &encoder,
            &QualityPreset::Draft,
            &settings,
            "/input.mp4",
            "/output.mp4",
        );

        let ss_idx = cmd.args.iter().position(|a| a == "-ss").unwrap();
        assert_eq!(cmd.args[ss_idx + 1], "10.500000");

        let t_idx = cmd.args.iter().position(|a| a == "-t").unwrap();
        assert_eq!(cmd.args[t_idx + 1], "9.500000");
    }

    #[test]
    fn build_render_command_with_hardware_encoder() {
        let segment = test_segment(0, 0.0, 3.0);
        let encoder = EncoderInfo {
            name: "h264_nvenc".to_string(),
            codec: "h264".to_string(),
            is_hardware: true,
            encoder_type: EncoderType::Nvenc,
            description: "NVIDIA NVENC".to_string(),
        };
        let settings = test_settings();
        let cmd = build_render_command(
            &segment,
            &encoder,
            &QualityPreset::High,
            &settings,
            "/input.mp4",
            "/output.mp4",
        );

        assert!(cmd.args.contains(&"h264_nvenc".to_string()));
        // NVENC high quality uses p7 preset
        assert!(cmd.args.contains(&"p7".to_string()));
    }

    // -- build_concat_command tests --

    #[test]
    fn build_concat_command_generates_valid_ffconcat() {
        let segments = vec![
            "/output/seg_000.mp4".to_string(),
            "/output/seg_001.mp4".to_string(),
            "/output/seg_002.mp4".to_string(),
        ];
        let result = build_concat_command(&segments, "/output/final.mp4", "/tmp/concat.txt");

        assert!(result
            .concat_file_content
            .starts_with("ffconcat version 1.0\n"));
        assert!(result
            .concat_file_content
            .contains("file /output/seg_000.mp4\n"));
        assert!(result
            .concat_file_content
            .contains("file /output/seg_001.mp4\n"));
        assert!(result
            .concat_file_content
            .contains("file /output/seg_002.mp4\n"));
    }

    #[test]
    fn build_concat_command_uses_safe_zero() {
        let segments = vec!["/output/seg_000.mp4".to_string()];
        let result = build_concat_command(&segments, "/output/final.mp4", "/tmp/concat.txt");

        assert!(result.args.contains(&"-safe".to_string()));
        assert!(result.args.contains(&"0".to_string()));
    }

    #[test]
    fn build_concat_command_windows_paths_converted() {
        let segments = vec![
            r"C:\Users\user\output\seg_000.mp4".to_string(),
            r"D:\media\seg_001.mp4".to_string(),
        ];
        let result = build_concat_command(&segments, "/output/final.mp4", "/tmp/concat.txt");

        assert!(result
            .concat_file_content
            .contains("file C:/Users/user/output/seg_000.mp4\n"));
        assert!(result
            .concat_file_content
            .contains("file D:/media/seg_001.mp4\n"));
        // No backslashes in file content
        assert!(!result.concat_file_content.contains('\\'));
    }

    #[test]
    fn build_concat_command_args_structure() {
        let segments = vec!["/seg.mp4".to_string()];
        let result = build_concat_command(&segments, "/final.mp4", "/tmp/concat.txt");

        assert_eq!(result.args[0], "-f");
        assert_eq!(result.args[1], "concat");
        assert!(result.args.contains(&"-i".to_string()));
        assert!(result.args.contains(&"/tmp/concat.txt".to_string()));
        assert!(result.args.contains(&"-c".to_string()));
        assert!(result.args.contains(&"copy".to_string()));
        assert!(result.args.contains(&"-y".to_string()));
        assert_eq!(result.args.last().unwrap(), "/final.mp4");
    }

    // -- check_output_conflict tests --

    #[test]
    fn check_output_conflict_nonexistent_file() {
        assert!(!check_output_conflict(
            "/nonexistent/path/that/does/not/exist.mp4"
        ));
    }

    #[test]
    fn check_output_conflict_existing_file() {
        // Cargo.toml always exists in the project
        assert!(check_output_conflict("Cargo.toml"));
    }

    // -- estimate_output_size tests --

    #[test]
    fn estimate_output_size_x264_standard() {
        // 10s * 5Mbps / 8 * 1.2 = 7_500_000 bytes
        let size = estimate_output_size(10.0, "libx264", "standard");
        assert_eq!(size, 7_500_000);
    }

    #[test]
    fn estimate_output_size_x264_draft() {
        // 10s * 2Mbps / 8 * 1.2 = 3_000_000 bytes
        let size = estimate_output_size(10.0, "libx264", "draft");
        assert_eq!(size, 3_000_000);
    }

    #[test]
    fn estimate_output_size_x264_high() {
        // 10s * 10Mbps / 8 * 1.2 = 15_000_000 bytes
        let size = estimate_output_size(10.0, "libx264", "high");
        assert_eq!(size, 15_000_000);
    }

    #[test]
    fn estimate_output_size_x265_has_lower_bitrate() {
        let x264_size = estimate_output_size(10.0, "libx264", "standard");
        let x265_size = estimate_output_size(10.0, "libx265", "standard");
        assert!(x265_size < x264_size);
        // x265 is 60% of x264
        assert_eq!(x265_size, (x264_size as f64 * 0.6) as u64);
    }

    #[test]
    fn estimate_output_size_vp9_has_lower_bitrate() {
        let x264_size = estimate_output_size(10.0, "libx264", "standard");
        let vp9_size = estimate_output_size(10.0, "libvpx-vp9", "standard");
        assert!(vp9_size < x264_size);
    }

    #[test]
    fn estimate_output_size_av1_smallest() {
        let x264_size = estimate_output_size(10.0, "libx264", "standard");
        let av1_size = estimate_output_size(10.0, "libaom-av1", "standard");
        assert!(av1_size < x264_size);
        // av1 is 50% of x264
        assert_eq!(av1_size, (x264_size as f64 * 0.5) as u64);
    }

    #[test]
    fn estimate_output_size_proportional_to_duration() {
        let size_10s = estimate_output_size(10.0, "libx264", "standard");
        let size_20s = estimate_output_size(20.0, "libx264", "standard");
        assert_eq!(size_20s, size_10s * 2);
    }

    #[test]
    fn estimate_output_size_zero_duration() {
        assert_eq!(estimate_output_size(0.0, "libx264", "standard"), 0);
    }

    #[test]
    fn estimate_output_size_unknown_codec_falls_back() {
        // Unknown codec uses x264 base rates
        let unknown = estimate_output_size(10.0, "unknown_codec", "standard");
        let x264 = estimate_output_size(10.0, "libx264", "standard");
        assert_eq!(unknown, x264);
    }

    #[test]
    fn estimate_output_size_unknown_preset_falls_back() {
        // Unknown preset uses standard base rate
        let unknown = estimate_output_size(10.0, "libx264", "unknown_preset");
        let standard = estimate_output_size(10.0, "libx264", "standard");
        assert_eq!(unknown, standard);
    }

    // -- Contract tests --

    #[test]
    fn concat_file_content_format_validation() {
        let segments = vec!["/a/seg0.mp4".to_string(), "/b/seg1.mp4".to_string()];
        let result = build_concat_command(&segments, "/out.mp4", "/tmp/list.txt");
        let content = &result.concat_file_content;

        // Must start with version header
        let lines: Vec<&str> = content.lines().collect();
        assert_eq!(lines[0], "ffconcat version 1.0");

        // Each subsequent line is a file entry
        for line in &lines[1..] {
            assert!(
                line.starts_with("file "),
                "Expected 'file ' prefix, got: {line}"
            );
            // No backslashes
            assert!(!line.contains('\\'), "Backslash found in: {line}");
        }

        // File count matches segments
        let file_lines: Vec<&&str> = lines.iter().filter(|l| l.starts_with("file ")).collect();
        assert_eq!(file_lines.len(), segments.len());
    }

    // -- PyO3 binding tests --

    #[test]
    fn pyo3_build_render_command_callable() {
        pyo3::prepare_freethreaded_python();
        pyo3::Python::with_gil(|py| {
            let segment = RenderSegment::new(0, 0.0, 5.0, 150, 150.0);
            let encoder = test_encoder();
            let settings = test_settings();

            let cmd = build_render_command(
                &segment,
                &encoder,
                &QualityPreset::Standard,
                &settings,
                "/input.mp4",
                "/output.mp4",
            );

            // Convert to Python to verify it's a valid PyO3 object
            let py_cmd = cmd.into_pyobject(py).unwrap();
            let output: String = py_cmd.getattr("output_path").unwrap().extract().unwrap();
            assert_eq!(output, "/output.mp4");

            let idx: usize = py_cmd.getattr("segment_index").unwrap().extract().unwrap();
            assert_eq!(idx, 0);

            let args: Vec<String> = py_cmd.call_method0("args").unwrap().extract().unwrap();
            assert!(!args.is_empty());
        });
    }

    #[test]
    fn pyo3_build_concat_command_callable() {
        pyo3::prepare_freethreaded_python();
        pyo3::Python::with_gil(|py| {
            let segments = vec!["/seg0.mp4".to_string(), "/seg1.mp4".to_string()];
            let result = build_concat_command(&segments, "/final.mp4", "/tmp/list.txt");

            let py_result = result.into_pyobject(py).unwrap();
            let content: String = py_result
                .getattr("concat_file_content")
                .unwrap()
                .extract()
                .unwrap();
            assert!(content.starts_with("ffconcat version 1.0"));

            let args: Vec<String> = py_result.call_method0("args").unwrap().extract().unwrap();
            assert!(!args.is_empty());
        });
    }

    #[test]
    fn pyo3_check_output_conflict_callable() {
        pyo3::prepare_freethreaded_python();
        // Just verify the function exists and returns a bool
        let result = check_output_conflict("/nonexistent.mp4");
        assert!(!result);
    }

    #[test]
    fn pyo3_estimate_output_size_callable() {
        pyo3::prepare_freethreaded_python();
        let result = estimate_output_size(10.0, "libx264", "standard");
        assert!(result > 0);
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use crate::render::encoder::EncoderType;
    use proptest::prelude::*;

    fn arb_segment() -> impl Strategy<Value = RenderSegment> {
        (0..100usize, 0.0..1000.0f64, 0.001..500.0f64).prop_map(|(index, start, duration)| {
            let end = start + duration;
            let frame_count = (duration * 30.0) as u64;
            RenderSegment::new(
                index,
                start,
                end,
                frame_count.max(1),
                frame_count.max(1) as f64,
            )
        })
    }

    fn arb_encoder() -> impl Strategy<Value = EncoderInfo> {
        prop_oneof![
            Just(EncoderInfo {
                name: "libx264".into(),
                codec: "h264".into(),
                is_hardware: false,
                encoder_type: EncoderType::Software,
                description: "x264".into(),
            }),
            Just(EncoderInfo {
                name: "h264_nvenc".into(),
                codec: "h264".into(),
                is_hardware: true,
                encoder_type: EncoderType::Nvenc,
                description: "nvenc".into(),
            }),
            Just(EncoderInfo {
                name: "libx265".into(),
                codec: "hevc".into(),
                is_hardware: false,
                encoder_type: EncoderType::Software,
                description: "x265".into(),
            }),
        ]
    }

    fn arb_quality() -> impl Strategy<Value = QualityPreset> {
        prop_oneof![
            Just(QualityPreset::Draft),
            Just(QualityPreset::Standard),
            Just(QualityPreset::High),
        ]
    }

    fn arb_settings() -> impl Strategy<Value = RenderSettings> {
        (
            prop_oneof![Just("mp4"), Just("mkv"), Just("webm")],
            1..8000u32,
            1..8000u32,
            prop_oneof![Just("libx264"), Just("libx265"), Just("libvpx-vp9")],
            prop_oneof![Just("medium"), Just("fast"), Just("slow")],
            1.0..120.0f64,
        )
            .prop_map(|(fmt, w, h, codec, preset, fps)| {
                RenderSettings::new(
                    fmt.to_string(),
                    w,
                    h,
                    codec.to_string(),
                    preset.to_string(),
                    fps,
                )
            })
    }

    proptest! {
        #[test]
        fn command_always_produces_nonempty_args(
            segment in arb_segment(),
            encoder in arb_encoder(),
            quality in arb_quality(),
            settings in arb_settings(),
        ) {
            let cmd = build_render_command(
                &segment, &encoder, &quality, &settings,
                "/input.mp4", "/output.mp4",
            );
            prop_assert!(!cmd.args.is_empty());
            // Must contain input, seek, codec, format, progress, output
            prop_assert!(cmd.args.contains(&"-i".to_string()));
            prop_assert!(cmd.args.contains(&"-ss".to_string()));
            prop_assert!(cmd.args.contains(&"-c:v".to_string()));
            prop_assert!(cmd.args.contains(&"-f".to_string()));
            prop_assert!(cmd.args.contains(&"-progress".to_string()));
        }

        #[test]
        fn size_estimate_always_positive_and_finite(
            duration in 0.001..100_000.0f64,
            codec in prop_oneof![
                Just("libx264"),
                Just("libx265"),
                Just("libvpx-vp9"),
                Just("libaom-av1"),
            ],
            quality in prop_oneof![
                Just("draft"),
                Just("standard"),
                Just("high"),
            ],
        ) {
            let size = estimate_output_size(duration, codec, quality);
            prop_assert!(size > 0, "Size must be positive for duration {duration}");
        }

        #[test]
        fn concat_always_starts_with_version_header(
            count in 1..20usize,
        ) {
            let segments: Vec<String> = (0..count).map(|i| format!("/seg_{i}.mp4")).collect();
            let result = build_concat_command(&segments, "/final.mp4", "/tmp/list.txt");
            prop_assert!(result.concat_file_content.starts_with("ffconcat version 1.0\n"));
            let file_lines = result.concat_file_content.lines().filter(|l| l.starts_with("file ")).count();
            prop_assert_eq!(file_lines, count);
        }
    }
}
