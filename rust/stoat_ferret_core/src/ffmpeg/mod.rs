//! FFmpeg command building and argument construction.
//!
//! This module provides a type-safe builder for constructing FFmpeg commands
//! that can be executed via subprocess.
//!
//! - [`FFmpegCommand`] - Builder for constructing FFmpeg argument arrays
//! - [`CommandError`] - Errors that can occur during command building
//! - [`filter`] - Filter chain builder for `-filter_complex` arguments
//!
//! # Design
//!
//! Commands are built as `Vec<String>` rather than shell strings to:
//! - Avoid shell escaping issues
//! - Enable direct use with `std::process::Command`
//! - Ensure proper handling of paths with spaces or special characters
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::FFmpegCommand;
//!
//! let args = FFmpegCommand::new()
//!     .overwrite(true)
//!     .input("input.mp4")
//!     .seek(10.0)
//!     .output("output.mp4")
//!     .video_codec("libx264")
//!     .preset("fast")
//!     .crf(23)
//!     .build()
//!     .expect("Valid command");
//!
//! assert!(args.contains(&"-y".to_string()));
//! assert!(args.contains(&"-ss".to_string()));
//! ```
//!
//! # Filter Chains
//!
//! Use the [`filter`] module to build complex filter graphs:
//!
//! ```
//! use stoat_ferret_core::ffmpeg::{FFmpegCommand, filter::{FilterGraph, FilterChain, scale}};
//!
//! let graph = FilterGraph::new()
//!     .chain(
//!         FilterChain::new()
//!             .input("0:v")
//!             .filter(scale(1280, 720))
//!             .output("scaled")
//!     );
//!
//! let args = FFmpegCommand::new()
//!     .input("input.mp4")
//!     .filter_complex(graph.to_string())
//!     .output("output.mp4")
//!     .map("[scaled]")
//!     .build()
//!     .expect("Valid command");
//! ```

pub mod audio;
mod command;
pub mod drawtext;
pub mod expression;
pub mod filter;
pub mod speed;
pub mod transitions;

pub use command::{CommandError, FFmpegCommand};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_transcode() {
        let args = FFmpegCommand::new()
            .overwrite(true)
            .input("input.mp4")
            .output("output.mp4")
            .video_codec("libx264")
            .build()
            .expect("Valid command");

        assert_eq!(
            args,
            vec!["-y", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"]
        );
    }

    #[test]
    fn test_trim_with_seek() {
        let args = FFmpegCommand::new()
            .input("source.mp4")
            .seek(10.5)
            .duration(5.0)
            .output("trimmed.mp4")
            .build()
            .expect("Valid command");

        assert_eq!(
            args,
            vec![
                "-ss",
                "10.500",
                "-t",
                "5.000",
                "-i",
                "source.mp4",
                "trimmed.mp4"
            ]
        );
    }

    #[test]
    fn test_full_encode_options() {
        let args = FFmpegCommand::new()
            .overwrite(true)
            .loglevel("warning")
            .input("input.mp4")
            .output("output.mp4")
            .video_codec("libx264")
            .audio_codec("aac")
            .preset("slow")
            .crf(18)
            .format("mp4")
            .build()
            .expect("Valid command");

        assert_eq!(
            args,
            vec![
                "-y",
                "-loglevel",
                "warning",
                "-i",
                "input.mp4",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-preset",
                "slow",
                "-crf",
                "18",
                "-f",
                "mp4",
                "output.mp4"
            ]
        );
    }

    #[test]
    fn test_multiple_inputs() {
        let args = FFmpegCommand::new()
            .input("video.mp4")
            .input("audio.wav")
            .output("combined.mp4")
            .build()
            .expect("Valid command");

        assert_eq!(
            args,
            vec!["-i", "video.mp4", "-i", "audio.wav", "combined.mp4"]
        );
    }

    #[test]
    fn test_stream_loop() {
        let args = FFmpegCommand::new()
            .input("short.mp4")
            .stream_loop(3)
            .output("looped.mp4")
            .build()
            .expect("Valid command");

        assert_eq!(
            args,
            vec!["-stream_loop", "3", "-i", "short.mp4", "looped.mp4"]
        );
    }

    #[test]
    fn test_filter_complex() {
        let args = FFmpegCommand::new()
            .input("input.mp4")
            .filter_complex("[0:v]scale=1280:720[scaled]")
            .output("scaled.mp4")
            .map("[scaled]")
            .build()
            .expect("Valid command");

        assert!(args.contains(&"-filter_complex".to_string()));
        assert!(args.contains(&"[0:v]scale=1280:720[scaled]".to_string()));
        assert!(args.contains(&"-map".to_string()));
        assert!(args.contains(&"[scaled]".to_string()));
    }

    #[test]
    fn test_validation_no_inputs() {
        let result = FFmpegCommand::new().output("output.mp4").build();

        assert_eq!(result, Err(CommandError::NoInputs));
    }

    #[test]
    fn test_validation_no_outputs() {
        let result = FFmpegCommand::new().input("input.mp4").build();

        assert_eq!(result, Err(CommandError::NoOutputs));
    }

    #[test]
    fn test_validation_empty_input_path() {
        let result = FFmpegCommand::new().input("").output("output.mp4").build();

        assert_eq!(result, Err(CommandError::EmptyPath));
    }

    #[test]
    fn test_validation_empty_output_path() {
        let result = FFmpegCommand::new().input("input.mp4").output("").build();

        assert_eq!(result, Err(CommandError::EmptyPath));
    }

    #[test]
    fn test_validation_crf_too_high() {
        let result = FFmpegCommand::new()
            .input("input.mp4")
            .output("output.mp4")
            .crf(52)
            .build();

        assert_eq!(result, Err(CommandError::InvalidCrf(52)));
    }

    #[test]
    fn test_crf_boundary_valid() {
        // CRF 51 is the maximum valid value
        let result = FFmpegCommand::new()
            .input("input.mp4")
            .output("output.mp4")
            .crf(51)
            .build();

        assert!(result.is_ok());
    }

    #[test]
    fn test_crf_zero_valid() {
        // CRF 0 is valid (lossless)
        let result = FFmpegCommand::new()
            .input("input.mp4")
            .output("output.mp4")
            .crf(0)
            .build();

        assert!(result.is_ok());
    }
}
