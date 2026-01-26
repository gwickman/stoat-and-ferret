//! FFmpeg command builder implementation.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::fmt;

/// A type-safe builder for constructing FFmpeg command arguments.
///
/// This builder creates argument arrays suitable for passing to `std::process::Command`
/// without requiring shell escaping.
///
/// # Builder Pattern
///
/// Input and output specifications are added sequentially, with options applying
/// to the most recently added input or output:
///
/// ```
/// use stoat_ferret_core::ffmpeg::FFmpegCommand;
///
/// let args = FFmpegCommand::new()
///     .input("first.mp4")
///     .seek(5.0)          // applies to first.mp4
///     .input("second.mp4")
///     .seek(10.0)         // applies to second.mp4
///     .output("combined.mp4")
///     .video_codec("libx264")
///     .build()
///     .expect("Valid command");
/// ```
///
/// # Validation
///
/// The builder validates commands on `build()`:
/// - At least one input is required
/// - At least one output is required
/// - Paths must be non-empty
/// - CRF must be in range 0-51
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Default)]
pub struct FFmpegCommand {
    overwrite: bool,
    loglevel: Option<String>,
    inputs: Vec<InputSpec>,
    outputs: Vec<OutputSpec>,
    filter_complex: Option<String>,
}

/// Specification for an input file.
#[derive(Debug, Clone)]
struct InputSpec {
    path: String,
    seek: Option<f64>,
    duration: Option<f64>,
    stream_loop: Option<i32>,
}

/// Specification for an output file.
#[derive(Debug, Clone)]
struct OutputSpec {
    path: String,
    video_codec: Option<String>,
    audio_codec: Option<String>,
    preset: Option<String>,
    crf: Option<u8>,
    format: Option<String>,
    maps: Vec<String>,
}

/// Errors that can occur when building an FFmpeg command.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CommandError {
    /// No input files were specified.
    NoInputs,
    /// No output files were specified.
    NoOutputs,
    /// An input or output path was empty.
    EmptyPath,
    /// CRF value is out of valid range (0-51).
    InvalidCrf(u8),
}

impl fmt::Display for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CommandError::NoInputs => write!(f, "At least one input file is required"),
            CommandError::NoOutputs => write!(f, "At least one output file is required"),
            CommandError::EmptyPath => write!(f, "File path cannot be empty"),
            CommandError::InvalidCrf(crf) => {
                write!(f, "CRF value {crf} is out of range (must be 0-51)")
            }
        }
    }
}

impl std::error::Error for CommandError {}

impl FFmpegCommand {
    /// Creates a new empty FFmpeg command builder.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new();
    /// ```
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Sets the overwrite flag (`-y`).
    ///
    /// When true, FFmpeg will overwrite output files without prompting.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .overwrite(true)
    ///     .input("in.mp4")
    ///     .output("out.mp4")
    ///     .build()
    ///     .expect("Valid command");
    ///
    /// assert!(cmd.contains(&"-y".to_string()));
    /// ```
    #[must_use]
    pub fn overwrite(mut self, yes: bool) -> Self {
        self.overwrite = yes;
        self
    }

    /// Sets the log level (`-loglevel`).
    ///
    /// Common values: "quiet", "panic", "fatal", "error", "warning", "info", "verbose", "debug".
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .loglevel("warning")
    ///     .input("in.mp4")
    ///     .output("out.mp4")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn loglevel(mut self, level: impl Into<String>) -> Self {
        self.loglevel = Some(level.into());
        self
    }

    /// Adds an input file (`-i`).
    ///
    /// Input options like `seek()` and `duration()` apply to the most recently added input.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .input("audio.wav")
    ///     .output("combined.mp4")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn input(mut self, path: impl Into<String>) -> Self {
        self.inputs.push(InputSpec {
            path: path.into(),
            seek: None,
            duration: None,
            stream_loop: None,
        });
        self
    }

    /// Sets the seek position (`-ss`) for the most recent input.
    ///
    /// Seeks to the specified position in seconds before decoding.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .seek(30.5)  // Start at 30.5 seconds
    ///     .output("trimmed.mp4")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn seek(mut self, seconds: f64) -> Self {
        if let Some(input) = self.inputs.last_mut() {
            input.seek = Some(seconds);
        }
        self
    }

    /// Sets the duration limit (`-t`) for the most recent input.
    ///
    /// Limits the duration of data read from the input.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .seek(10.0)
    ///     .duration(5.0)  // Read 5 seconds
    ///     .output("clip.mp4")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn duration(mut self, seconds: f64) -> Self {
        if let Some(input) = self.inputs.last_mut() {
            input.duration = Some(seconds);
        }
        self
    }

    /// Sets the stream loop count (`-stream_loop`) for the most recent input.
    ///
    /// Loops the input stream the specified number of times.
    /// Use -1 for infinite looping.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("short.mp4")
    ///     .stream_loop(3)  // Loop 3 times
    ///     .output("extended.mp4")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn stream_loop(mut self, count: i32) -> Self {
        if let Some(input) = self.inputs.last_mut() {
            input.stream_loop = Some(count);
        }
        self
    }

    /// Adds an output file.
    ///
    /// Output options like `video_codec()`, `preset()`, etc. apply to the most recently added output.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("output.mp4")
    ///     .video_codec("libx264")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn output(mut self, path: impl Into<String>) -> Self {
        self.outputs.push(OutputSpec {
            path: path.into(),
            video_codec: None,
            audio_codec: None,
            preset: None,
            crf: None,
            format: None,
            maps: Vec::new(),
        });
        self
    }

    /// Sets the video codec (`-c:v`) for the most recent output.
    ///
    /// Common values: "libx264", "libx265", "copy", "vp9", "av1".
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("encoded.mp4")
    ///     .video_codec("libx265")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn video_codec(mut self, codec: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.video_codec = Some(codec.into());
        }
        self
    }

    /// Sets the audio codec (`-c:a`) for the most recent output.
    ///
    /// Common values: "aac", "libmp3lame", "copy", "flac", "opus".
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("encoded.mp4")
    ///     .audio_codec("aac")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn audio_codec(mut self, codec: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.audio_codec = Some(codec.into());
        }
        self
    }

    /// Sets the encoding preset (`-preset`) for the most recent output.
    ///
    /// Common values: "ultrafast", "superfast", "veryfast", "faster", "fast",
    /// "medium", "slow", "slower", "veryslow".
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("encoded.mp4")
    ///     .video_codec("libx264")
    ///     .preset("fast")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn preset(mut self, preset: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.preset = Some(preset.into());
        }
        self
    }

    /// Sets the CRF quality level (`-crf`) for the most recent output.
    ///
    /// Valid range: 0-51. Lower values mean higher quality.
    /// - 0 = lossless
    /// - 18 = visually lossless
    /// - 23 = default
    /// - 28 = lower quality
    /// - 51 = worst quality
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("encoded.mp4")
    ///     .video_codec("libx264")
    ///     .crf(23)
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn crf(mut self, crf: u8) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.crf = Some(crf);
        }
        self
    }

    /// Sets the output format (`-f`) for the most recent output.
    ///
    /// Common values: "mp4", "matroska", "webm", "avi", "mov".
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .output("output.mkv")
    ///     .format("matroska")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn format(mut self, format: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.format = Some(format.into());
        }
        self
    }

    /// Sets a complex filtergraph (`-filter_complex`).
    ///
    /// This is used for complex filter graphs that involve multiple inputs
    /// or outputs.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .filter_complex("[0:v]scale=1280:720[scaled]")
    ///     .output("scaled.mp4")
    ///     .map("[scaled]")
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn filter_complex(mut self, filter: impl Into<String>) -> Self {
        self.filter_complex = Some(filter.into());
        self
    }

    /// Adds a stream mapping (`-map`) for the most recent output.
    ///
    /// Used to select which streams from the inputs go to the output.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let cmd = FFmpegCommand::new()
    ///     .input("video.mp4")
    ///     .input("audio.wav")
    ///     .output("combined.mp4")
    ///     .map("0:v")  // Video from first input
    ///     .map("1:a")  // Audio from second input
    ///     .build()
    ///     .expect("Valid command");
    /// ```
    #[must_use]
    pub fn map(mut self, stream: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.maps.push(stream.into());
        }
        self
    }

    /// Builds the FFmpeg command arguments.
    ///
    /// Returns a `Vec<String>` suitable for passing to `std::process::Command`.
    /// Does not include the "ffmpeg" executable itself.
    ///
    /// # Errors
    ///
    /// Returns `CommandError` if validation fails:
    /// - `NoInputs` - No input files were specified
    /// - `NoOutputs` - No output files were specified
    /// - `EmptyPath` - An input or output path is empty
    /// - `InvalidCrf` - CRF value is out of range (0-51)
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::FFmpegCommand;
    ///
    /// let args = FFmpegCommand::new()
    ///     .input("input.mp4")
    ///     .output("output.mp4")
    ///     .build()
    ///     .expect("Valid command");
    ///
    /// assert_eq!(args, vec!["-i", "input.mp4", "output.mp4"]);
    /// ```
    pub fn build(&self) -> Result<Vec<String>, CommandError> {
        self.validate()?;

        let mut args = Vec::new();

        // Global options
        if self.overwrite {
            args.push("-y".to_string());
        }
        if let Some(ref level) = self.loglevel {
            args.push("-loglevel".to_string());
            args.push(level.clone());
        }

        // Input specifications
        for input in &self.inputs {
            if let Some(seek) = input.seek {
                args.push("-ss".to_string());
                args.push(format!("{seek:.3}"));
            }
            if let Some(dur) = input.duration {
                args.push("-t".to_string());
                args.push(format!("{dur:.3}"));
            }
            if let Some(loops) = input.stream_loop {
                args.push("-stream_loop".to_string());
                args.push(loops.to_string());
            }
            args.push("-i".to_string());
            args.push(input.path.clone());
        }

        // Filter complex
        if let Some(ref filter) = self.filter_complex {
            args.push("-filter_complex".to_string());
            args.push(filter.clone());
        }

        // Output specifications
        for output in &self.outputs {
            // Stream mappings come before other output options
            for map in &output.maps {
                args.push("-map".to_string());
                args.push(map.clone());
            }
            if let Some(ref codec) = output.video_codec {
                args.push("-c:v".to_string());
                args.push(codec.clone());
            }
            if let Some(ref codec) = output.audio_codec {
                args.push("-c:a".to_string());
                args.push(codec.clone());
            }
            if let Some(ref preset) = output.preset {
                args.push("-preset".to_string());
                args.push(preset.clone());
            }
            if let Some(crf) = output.crf {
                args.push("-crf".to_string());
                args.push(crf.to_string());
            }
            if let Some(ref fmt) = output.format {
                args.push("-f".to_string());
                args.push(fmt.clone());
            }
            args.push(output.path.clone());
        }

        Ok(args)
    }

    /// Validates the command configuration.
    fn validate(&self) -> Result<(), CommandError> {
        if self.inputs.is_empty() {
            return Err(CommandError::NoInputs);
        }
        if self.outputs.is_empty() {
            return Err(CommandError::NoOutputs);
        }
        for input in &self.inputs {
            if input.path.is_empty() {
                return Err(CommandError::EmptyPath);
            }
        }
        for output in &self.outputs {
            if output.path.is_empty() {
                return Err(CommandError::EmptyPath);
            }
            if let Some(crf) = output.crf {
                if crf > 51 {
                    return Err(CommandError::InvalidCrf(crf));
                }
            }
        }
        Ok(())
    }
}

#[pymethods]
impl FFmpegCommand {
    /// Creates a new empty FFmpeg command builder.
    #[new]
    fn py_new() -> Self {
        Self::new()
    }

    /// Sets the overwrite flag (`-y`).
    ///
    /// When true, FFmpeg will overwrite output files without prompting.
    /// Returns self to support method chaining.
    #[pyo3(name = "overwrite")]
    fn py_overwrite(mut slf: PyRefMut<'_, Self>, yes: bool) -> PyRefMut<'_, Self> {
        slf.overwrite = yes;
        slf
    }

    /// Sets the log level (`-loglevel`).
    ///
    /// Common values: "quiet", "panic", "fatal", "error", "warning", "info", "verbose", "debug".
    /// Returns self to support method chaining.
    #[pyo3(name = "loglevel")]
    fn py_loglevel(mut slf: PyRefMut<'_, Self>, level: String) -> PyRefMut<'_, Self> {
        slf.loglevel = Some(level);
        slf
    }

    /// Adds an input file (`-i`).
    ///
    /// Input options like `seek()` and `duration()` apply to the most recently added input.
    /// Returns self to support method chaining.
    #[pyo3(name = "input")]
    fn py_input(mut slf: PyRefMut<'_, Self>, path: String) -> PyRefMut<'_, Self> {
        slf.inputs.push(InputSpec {
            path,
            seek: None,
            duration: None,
            stream_loop: None,
        });
        slf
    }

    /// Sets the seek position (`-ss`) for the most recent input.
    ///
    /// Seeks to the specified position in seconds before decoding.
    /// Returns self to support method chaining.
    #[pyo3(name = "seek")]
    fn py_seek(mut slf: PyRefMut<'_, Self>, seconds: f64) -> PyRefMut<'_, Self> {
        if let Some(input) = slf.inputs.last_mut() {
            input.seek = Some(seconds);
        }
        slf
    }

    /// Sets the duration limit (`-t`) for the most recent input.
    ///
    /// Limits the duration of data read from the input.
    /// Returns self to support method chaining.
    #[pyo3(name = "duration")]
    fn py_duration(mut slf: PyRefMut<'_, Self>, seconds: f64) -> PyRefMut<'_, Self> {
        if let Some(input) = slf.inputs.last_mut() {
            input.duration = Some(seconds);
        }
        slf
    }

    /// Sets the stream loop count (`-stream_loop`) for the most recent input.
    ///
    /// Loops the input stream the specified number of times.
    /// Use -1 for infinite looping.
    /// Returns self to support method chaining.
    #[pyo3(name = "stream_loop")]
    fn py_stream_loop(mut slf: PyRefMut<'_, Self>, count: i32) -> PyRefMut<'_, Self> {
        if let Some(input) = slf.inputs.last_mut() {
            input.stream_loop = Some(count);
        }
        slf
    }

    /// Adds an output file.
    ///
    /// Output options like `video_codec()`, `preset()`, etc. apply to the most recently added output.
    /// Returns self to support method chaining.
    #[pyo3(name = "output")]
    fn py_output(mut slf: PyRefMut<'_, Self>, path: String) -> PyRefMut<'_, Self> {
        slf.outputs.push(OutputSpec {
            path,
            video_codec: None,
            audio_codec: None,
            preset: None,
            crf: None,
            format: None,
            maps: Vec::new(),
        });
        slf
    }

    /// Sets the video codec (`-c:v`) for the most recent output.
    ///
    /// Common values: "libx264", "libx265", "copy", "vp9", "av1".
    /// Returns self to support method chaining.
    #[pyo3(name = "video_codec")]
    fn py_video_codec(mut slf: PyRefMut<'_, Self>, codec: String) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.video_codec = Some(codec);
        }
        slf
    }

    /// Sets the audio codec (`-c:a`) for the most recent output.
    ///
    /// Common values: "aac", "libmp3lame", "copy", "flac", "opus".
    /// Returns self to support method chaining.
    #[pyo3(name = "audio_codec")]
    fn py_audio_codec(mut slf: PyRefMut<'_, Self>, codec: String) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.audio_codec = Some(codec);
        }
        slf
    }

    /// Sets the encoding preset (`-preset`) for the most recent output.
    ///
    /// Common values: "ultrafast", "superfast", "veryfast", "faster", "fast",
    /// "medium", "slow", "slower", "veryslow".
    /// Returns self to support method chaining.
    #[pyo3(name = "preset")]
    fn py_preset(mut slf: PyRefMut<'_, Self>, preset: String) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.preset = Some(preset);
        }
        slf
    }

    /// Sets the CRF quality level (`-crf`) for the most recent output.
    ///
    /// Valid range: 0-51. Lower values mean higher quality.
    /// Returns self to support method chaining.
    #[pyo3(name = "crf")]
    fn py_crf(mut slf: PyRefMut<'_, Self>, crf: u8) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.crf = Some(crf);
        }
        slf
    }

    /// Sets the output format (`-f`) for the most recent output.
    ///
    /// Common values: "mp4", "matroska", "webm", "avi", "mov".
    /// Returns self to support method chaining.
    #[pyo3(name = "format")]
    fn py_format(mut slf: PyRefMut<'_, Self>, format: String) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.format = Some(format);
        }
        slf
    }

    /// Sets a complex filtergraph (`-filter_complex`).
    ///
    /// This is used for complex filter graphs that involve multiple inputs or outputs.
    /// Returns self to support method chaining.
    #[pyo3(name = "filter_complex")]
    fn py_filter_complex(mut slf: PyRefMut<'_, Self>, filter: String) -> PyRefMut<'_, Self> {
        slf.filter_complex = Some(filter);
        slf
    }

    /// Adds a stream mapping (`-map`) for the most recent output.
    ///
    /// Used to select which streams from the inputs go to the output.
    /// Returns self to support method chaining.
    #[pyo3(name = "map")]
    fn py_map(mut slf: PyRefMut<'_, Self>, stream: String) -> PyRefMut<'_, Self> {
        if let Some(output) = slf.outputs.last_mut() {
            output.maps.push(stream);
        }
        slf
    }

    /// Builds the FFmpeg command arguments.
    ///
    /// Returns a list of strings suitable for passing to subprocess.
    /// Does not include the "ffmpeg" executable itself.
    ///
    /// # Raises
    ///
    /// ValueError: If validation fails (no inputs, no outputs, empty paths, invalid CRF)
    #[pyo3(name = "build")]
    fn py_build(&self) -> PyResult<Vec<String>> {
        self.build()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Returns a string representation of the command builder.
    fn __repr__(&self) -> String {
        format!(
            "FFmpegCommand(inputs={}, outputs={})",
            self.inputs.len(),
            self.outputs.len()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_empty() {
        let cmd = FFmpegCommand::new();
        assert!(cmd.inputs.is_empty());
        assert!(cmd.outputs.is_empty());
        assert!(!cmd.overwrite);
    }

    #[test]
    fn test_builder_is_clone() {
        let cmd = FFmpegCommand::new()
            .overwrite(true)
            .input("input.mp4")
            .output("output.mp4");

        let cloned = cmd.clone();
        assert_eq!(cloned.overwrite, cmd.overwrite);
        assert_eq!(cloned.inputs.len(), cmd.inputs.len());
    }

    #[test]
    fn test_error_display() {
        assert_eq!(
            CommandError::NoInputs.to_string(),
            "At least one input file is required"
        );
        assert_eq!(
            CommandError::NoOutputs.to_string(),
            "At least one output file is required"
        );
        assert_eq!(
            CommandError::EmptyPath.to_string(),
            "File path cannot be empty"
        );
        assert_eq!(
            CommandError::InvalidCrf(52).to_string(),
            "CRF value 52 is out of range (must be 0-51)"
        );
    }

    #[test]
    fn test_multiple_outputs() {
        let args = FFmpegCommand::new()
            .input("input.mp4")
            .output("output1.mp4")
            .video_codec("libx264")
            .output("output2.webm")
            .video_codec("vp9")
            .build()
            .expect("Valid command");

        // Check both outputs are present with their codecs
        assert!(args.contains(&"output1.mp4".to_string()));
        assert!(args.contains(&"output2.webm".to_string()));
        assert!(args.contains(&"libx264".to_string()));
        assert!(args.contains(&"vp9".to_string()));
    }

    #[test]
    fn test_input_options_apply_to_correct_input() {
        let args = FFmpegCommand::new()
            .input("first.mp4")
            .seek(5.0)
            .input("second.mp4")
            .seek(10.0)
            .output("output.mp4")
            .build()
            .expect("Valid command");

        // Find positions of seek values and input paths
        let ss_positions: Vec<usize> = args
            .iter()
            .enumerate()
            .filter_map(|(i, s)| if s == "-ss" { Some(i) } else { None })
            .collect();

        assert_eq!(ss_positions.len(), 2);
        // First seek should be followed by "5.000"
        assert_eq!(args[ss_positions[0] + 1], "5.000");
        // Second seek should be followed by "10.000"
        assert_eq!(args[ss_positions[1] + 1], "10.000");
    }

    #[test]
    fn test_seek_without_input_is_noop() {
        let cmd = FFmpegCommand::new().seek(5.0).input("input.mp4");

        // The seek should be ignored since there was no input to attach it to
        assert!(cmd.inputs[0].seek.is_none());
    }

    #[test]
    fn test_video_codec_without_output_is_noop() {
        let cmd = FFmpegCommand::new()
            .video_codec("libx264")
            .input("input.mp4")
            .output("output.mp4");

        // The codec should be ignored since there was no output to attach it to
        assert!(cmd.outputs[0].video_codec.is_none());
    }
}
