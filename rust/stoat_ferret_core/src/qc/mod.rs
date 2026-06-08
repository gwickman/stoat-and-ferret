//! QC measurement parsers for FFmpeg analysis filter output.
//!
//! Provides typed parsers for ebur128/loudnorm (loudness), astats/volumedetect
//! (peak), silencedetect, aspectralstats (spectral), and blackdetect/freezedetect
//! (video defects). All parsers return `PyResult<T>` and never panic.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::qc::{py_parse_loudness_report, py_parse_silence_report};
//!
//! let json = r#"{"input_i": "-16.23", "input_lra": "4.20", "input_tp": "-1.09"}"#;
//! // parse_loudness_report accepts both JSON field variants
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// Loudness measurements parsed from ebur128/loudnorm JSON output.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct LoudnessReport {
    /// Integrated loudness in LUFS.
    #[pyo3(get)]
    pub integrated_lufs: f64,
    /// Loudness range in LU.
    #[pyo3(get)]
    pub lra: f64,
    /// True peak in dBTP.
    #[pyo3(get)]
    pub true_peak_dbtp: f64,
}

/// Peak/clipping measurements parsed from astats/volumedetect output.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct PeakReport {
    /// Peak level in dB.
    #[pyo3(get)]
    pub peak_level: f64,
    /// Number of clipped samples (Peak count in astats, histogram_0db in volumedetect).
    #[pyo3(get)]
    pub clipped_samples: i64,
}

/// A single silence region with start and end times in seconds.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SilenceRegion {
    /// Start of silence in seconds.
    #[pyo3(get)]
    pub start: f64,
    /// End of silence in seconds.
    #[pyo3(get)]
    pub end: f64,
}

/// Silence analysis result containing all detected silence regions.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SilenceReport {
    pub(crate) regions: Vec<SilenceRegion>,
}

/// Per-channel spectral statistics parsed from aspectralstats output.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SpectralReport {
    /// Number of channels detected.
    #[pyo3(get)]
    pub channel_count: i64,
    /// Mean spectral energy per channel.
    #[pyo3(get)]
    pub channel_means: Vec<f64>,
}

/// A detected time region with start and end times in seconds.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Region {
    /// Start of region in seconds.
    #[pyo3(get)]
    pub start: f64,
    /// End of region in seconds.
    #[pyo3(get)]
    pub end: f64,
}

/// Video defect analysis result with black and freeze regions.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct VideoDefectReport {
    pub(crate) black_regions: Vec<Region>,
    pub(crate) freeze_regions: Vec<Region>,
}

// ---------------------------------------------------------------------------
// PyO3 method implementations
// ---------------------------------------------------------------------------

#[pymethods]
impl LoudnessReport {
    /// Creates a new LoudnessReport.
    #[new]
    fn py_new(integrated_lufs: f64, lra: f64, true_peak_dbtp: f64) -> Self {
        Self {
            integrated_lufs,
            lra,
            true_peak_dbtp,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "LoudnessReport(integrated_lufs={}, lra={}, true_peak_dbtp={})",
            self.integrated_lufs, self.lra, self.true_peak_dbtp
        )
    }
}

#[pymethods]
impl PeakReport {
    /// Creates a new PeakReport.
    #[new]
    fn py_new(peak_level: f64, clipped_samples: i64) -> Self {
        Self {
            peak_level,
            clipped_samples,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "PeakReport(peak_level={}, clipped_samples={})",
            self.peak_level, self.clipped_samples
        )
    }
}

#[pymethods]
impl SilenceRegion {
    /// Creates a new SilenceRegion.
    #[new]
    fn py_new(start: f64, end: f64) -> Self {
        Self { start, end }
    }

    fn __repr__(&self) -> String {
        format!("SilenceRegion(start={}, end={})", self.start, self.end)
    }
}

#[pymethods]
impl SilenceReport {
    /// Creates a new SilenceReport.
    #[new]
    fn py_new(regions: Vec<SilenceRegion>) -> Self {
        Self { regions }
    }

    /// Returns the list of silence regions.
    #[getter]
    fn regions(&self) -> Vec<SilenceRegion> {
        self.regions.clone()
    }

    fn __repr__(&self) -> String {
        format!("SilenceReport(regions=[{} items])", self.regions.len())
    }
}

#[pymethods]
impl SpectralReport {
    /// Creates a new SpectralReport.
    #[new]
    fn py_new(channel_count: i64, channel_means: Vec<f64>) -> Self {
        Self {
            channel_count,
            channel_means,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "SpectralReport(channel_count={}, channel_means={:?})",
            self.channel_count, self.channel_means
        )
    }
}

#[pymethods]
impl Region {
    /// Creates a new Region.
    #[new]
    fn py_new(start: f64, end: f64) -> Self {
        Self { start, end }
    }

    fn __repr__(&self) -> String {
        format!("Region(start={}, end={})", self.start, self.end)
    }
}

#[pymethods]
impl VideoDefectReport {
    /// Creates a new VideoDefectReport.
    #[new]
    fn py_new(black_regions: Vec<Region>, freeze_regions: Vec<Region>) -> Self {
        Self {
            black_regions,
            freeze_regions,
        }
    }

    /// Returns the list of black detection regions.
    #[getter]
    fn black_regions(&self) -> Vec<Region> {
        self.black_regions.clone()
    }

    /// Returns the list of freeze detection regions.
    #[getter]
    fn freeze_regions(&self) -> Vec<Region> {
        self.freeze_regions.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "VideoDefectReport(black_regions=[{} items], freeze_regions=[{} items])",
            self.black_regions.len(),
            self.freeze_regions.len()
        )
    }
}

// ---------------------------------------------------------------------------
// Internal parsing helpers
// ---------------------------------------------------------------------------

/// Extract a float value from JSON-like `"key": "str_value"` or `"key": num` formats.
fn extract_json_float(text: &str, key: &str) -> Option<f64> {
    let search = format!("\"{}\"", key);
    let key_pos = text.find(search.as_str())?;
    let after_key = &text[key_pos + search.len()..];
    let colon_pos = after_key.find(':')?;
    // colon is ASCII — colon_pos + 1 is always a valid char boundary
    let after_colon = after_key[colon_pos + 1..].trim_start();
    if let Some(inner) = after_colon.strip_prefix('"') {
        // Quoted string value
        let end = inner.find('"').unwrap_or(inner.len());
        inner[..end].trim().parse().ok()
    } else {
        // Numeric value
        let end = after_colon
            .find([',', '}', '\n', '\r'])
            .unwrap_or(after_colon.len());
        after_colon[..end].trim().parse().ok()
    }
}

/// Extract a float from an FFmpeg log line after a labeled prefix.
///
/// Handles `[filter @ addr] Label: -0.003` and `Label: -0.5 dB` forms.
fn extract_labeled_float(text: &str, label: &str) -> Option<f64> {
    let pos = text.find(label)?;
    let after = &text[pos + label.len()..];
    // Take the first whitespace-delimited token
    let token = after.split_whitespace().next()?;
    token.parse().ok()
}

/// Extract an integer from an FFmpeg log line after a labeled prefix.
fn extract_labeled_int(text: &str, label: &str) -> Option<i64> {
    let pos = text.find(label)?;
    let after = &text[pos + label.len()..];
    let token = after.split_whitespace().next()?;
    token.parse().ok()
}

/// Extract a float from a space-separated `key:value` pair (blackdetect format).
fn extract_kv_float(text: &str, key: &str) -> Option<f64> {
    let pos = text.find(key)?;
    let after = &text[pos + key.len()..];
    let end = after
        .find(|c: char| c.is_whitespace())
        .unwrap_or(after.len());
    after[..end].parse().ok()
}

// ---------------------------------------------------------------------------
// PyO3 parser functions
// ---------------------------------------------------------------------------

/// Parses ebur128/loudnorm JSON output into a `LoudnessReport`.
///
/// Accepts both `input_i` (FFmpeg ≥5.x) and `integrated_loudness` (FFmpeg ≤4.x)
/// field names. JSON values may be quoted strings or bare floats.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parse_loudness_report")]
pub fn py_parse_loudness_report(output: &str) -> PyResult<LoudnessReport> {
    let integrated = extract_json_float(output, "input_i")
        .or_else(|| extract_json_float(output, "integrated_loudness"))
        .ok_or_else(|| {
            PyValueError::new_err(
                "parse_loudness_report: missing 'input_i' or 'integrated_loudness' field",
            )
        })?;

    let lra = extract_json_float(output, "input_lra")
        .ok_or_else(|| PyValueError::new_err("parse_loudness_report: missing 'input_lra' field"))?;

    let peak = extract_json_float(output, "input_tp")
        .ok_or_else(|| PyValueError::new_err("parse_loudness_report: missing 'input_tp' field"))?;

    Ok(LoudnessReport {
        integrated_lufs: integrated,
        lra,
        true_peak_dbtp: peak,
    })
}

/// Parses astats/volumedetect text output into a `PeakReport`.
///
/// For astats: navigates to the "Overall" section and extracts "Peak level dB:"
/// and "Peak count:" fields. For volumedetect: extracts "max_volume:" and
/// "histogram_0db:" fields.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parse_peak_report")]
pub fn py_parse_peak_report(output: &str) -> PyResult<PeakReport> {
    // For astats, stats appear after the "Overall" marker.
    let search_text: &str = if output.contains("Overall") {
        let overall_pos = output.find("Overall").unwrap_or(0);
        &output[overall_pos..]
    } else {
        output
    };

    // "Peak level dB:" (astats Overall section) or "max_volume:" (volumedetect)
    let peak_level = extract_labeled_float(search_text, "Peak level dB:")
        .or_else(|| extract_labeled_float(output, "max_volume:"))
        .ok_or_else(|| {
            PyValueError::new_err(
                "parse_peak_report: missing 'Peak level dB:' or 'max_volume:' field",
            )
        })?;

    // "Peak count:" (astats) or "histogram_0db:" (volumedetect) — default to 0
    let clipped_samples = extract_labeled_int(search_text, "Peak count:")
        .or_else(|| extract_labeled_int(output, "histogram_0db:"))
        .unwrap_or(0);

    Ok(PeakReport {
        peak_level,
        clipped_samples,
    })
}

/// Parses silencedetect text output into a `SilenceReport`.
///
/// Pairs `silence_start:` and `silence_end:` lines in order. A trailing
/// `silence_start` without a matching `silence_end` produces a region with
/// `end: f64::MAX` (represents open-ended silence to stream end).
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parse_silence_report")]
pub fn py_parse_silence_report(output: &str) -> PyResult<SilenceReport> {
    let mut pending_starts: Vec<f64> = Vec::new();
    let mut regions: Vec<SilenceRegion> = Vec::new();

    for line in output.lines() {
        if line.contains("silence_start:") {
            if let Some(pos) = line.find("silence_start:") {
                let after = &line[pos + "silence_start:".len()..];
                if let Ok(start) = after.trim().parse::<f64>() {
                    pending_starts.push(start);
                }
            }
        } else if line.contains("silence_end:") {
            if let Some(pos) = line.find("silence_end:") {
                let after = &line[pos + "silence_end:".len()..];
                // Format: " 1.234567 | silence_duration: 1.111111"
                let end_str = after.split('|').next().unwrap_or("").trim();
                if let Ok(end) = end_str.parse::<f64>() {
                    if !pending_starts.is_empty() {
                        let start = pending_starts.remove(0);
                        regions.push(SilenceRegion { start, end });
                    }
                }
            }
        }
    }

    // Trailing starts without a matching end
    for start in pending_starts {
        regions.push(SilenceRegion {
            start,
            end: f64::MAX,
        });
    }

    Ok(SilenceReport { regions })
}

/// Parses aspectralstats lavfi key=value output into a `SpectralReport`.
///
/// Extracts per-channel mean spectral energy from lines of the form:
/// `lavfi.aspectralstats.{channel}.mean={value}`.
/// Returns an error if no channel data is found.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parse_spectral_report")]
pub fn py_parse_spectral_report(output: &str) -> PyResult<SpectralReport> {
    // Use BTreeMap so channels are ordered by number
    let mut channel_means: std::collections::BTreeMap<i64, f64> = std::collections::BTreeMap::new();

    for line in output.lines() {
        let line = line.trim();
        let prefix = "lavfi.aspectralstats.";
        if let Some(rest) = line.strip_prefix(prefix) {
            // rest is like "1.mean=0.001234" or "1.variance=0.000056"
            // Split on first '.' to get channel number
            let dot_pos = rest.find('.');
            if let Some(dp) = dot_pos {
                let channel_str = &rest[..dp];
                let stat_and_value = &rest[dp + 1..];
                if let Ok(channel) = channel_str.parse::<i64>() {
                    // Only capture .mean= entries for channel energy summary
                    if let Some(val_str) = stat_and_value.strip_prefix("mean=") {
                        if let Ok(mean) = val_str.trim().parse::<f64>() {
                            // Keep the first mean per channel (first frame)
                            channel_means.entry(channel).or_insert(mean);
                        }
                    }
                }
            }
        }
    }

    if channel_means.is_empty() {
        return Err(PyValueError::new_err(
            "parse_spectral_report: no 'lavfi.aspectralstats.*.mean' data found",
        ));
    }

    let channel_count = channel_means.len() as i64;
    let means: Vec<f64> = channel_means.into_values().collect();

    Ok(SpectralReport {
        channel_count,
        channel_means: means,
    })
}

/// Parses blackdetect and freezedetect text output into a `VideoDefectReport`.
///
/// blackdetect lines: `black_start:X black_end:Y black_duration:Z` (space-separated).
/// freezedetect lines: `lavfi.freezedetect.freeze_start: X` / `freeze_end: X` key=value.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parse_video_defect_report")]
pub fn py_parse_video_defect_report(output: &str) -> PyResult<VideoDefectReport> {
    let mut black_regions: Vec<Region> = Vec::new();
    let mut freeze_regions: Vec<Region> = Vec::new();
    let mut pending_freeze_starts: Vec<f64> = Vec::new();

    for line in output.lines() {
        // blackdetect: single line with all three fields
        if line.contains("black_start:") && line.contains("black_end:") {
            if let (Some(start), Some(end)) = (
                extract_kv_float(line, "black_start:"),
                extract_kv_float(line, "black_end:"),
            ) {
                black_regions.push(Region { start, end });
            }
        }
        // freezedetect start
        else if line.contains("lavfi.freezedetect.freeze_start:") {
            if let Some(pos) = line.find("lavfi.freezedetect.freeze_start:") {
                let after = &line[pos + "lavfi.freezedetect.freeze_start:".len()..];
                if let Ok(start) = after.trim().parse::<f64>() {
                    pending_freeze_starts.push(start);
                }
            }
        }
        // freezedetect end
        else if line.contains("lavfi.freezedetect.freeze_end:") {
            if let Some(pos) = line.find("lavfi.freezedetect.freeze_end:") {
                let after = &line[pos + "lavfi.freezedetect.freeze_end:".len()..];
                if let Ok(end) = after.trim().parse::<f64>() {
                    if !pending_freeze_starts.is_empty() {
                        let start = pending_freeze_starts.remove(0);
                        freeze_regions.push(Region { start, end });
                    }
                }
            }
        }
    }

    // Trailing freeze starts without matching ends
    for start in pending_freeze_starts {
        freeze_regions.push(Region {
            start,
            end: f64::MAX,
        });
    }

    Ok(VideoDefectReport {
        black_regions,
        freeze_regions,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- Fixtures from interface-contracts.md --

    const LOUDNORM_JSON_INPUT_I: &str = r#"
{
  "input_i": "-16.23",
  "input_lra": "4.20",
  "input_tp": "-1.09",
  "input_thresh": "-26.24",
  "output_i": "-16.23",
  "output_lra": "4.20",
  "output_tp": "-1.09",
  "output_thresh": "-26.24",
  "normalization_type": "dynamic",
  "target_offset": "0.23"
}
"#;

    const LOUDNORM_JSON_INTEGRATED_LOUDNESS: &str = r#"
{
  "integrated_loudness": "-14.82",
  "input_lra": "9.10",
  "input_tp": "-0.84",
  "input_thresh": "-24.82",
  "target_offset": "-1.18"
}
"#;

    const ASTATS_TEXT: &str = r#"
[Parsed_astats_0 @ 0x7f001] Channel 1
[Parsed_astats_0 @ 0x7f001] DC offset:  0.000000
[Parsed_astats_0 @ 0x7f001] Peak level dB: -3.200
[Parsed_astats_0 @ 0x7f001] Peak count: 0
[Parsed_astats_0 @ 0x7f001] Overall
[Parsed_astats_0 @ 0x7f001] DC offset:  0.000000
[Parsed_astats_0 @ 0x7f001] Peak level dB: -0.003
[Parsed_astats_0 @ 0x7f001] Peak count: 12
"#;

    const VOLUMEDETECT_TEXT: &str = r#"
[Parsed_volumedetect_0 @ 0x7f001] mean_volume: -16.2 dB
[Parsed_volumedetect_0 @ 0x7f001] max_volume: -0.5 dB
[Parsed_volumedetect_0 @ 0x7f001] histogram_0db: 0
[Parsed_volumedetect_0 @ 0x7f001] histogram_1db: 12
"#;

    const SILENCE_TEXT: &str = r#"
[silencedetect @ 0x7f001] silence_start: 0.123456
[silencedetect @ 0x7f001] silence_end: 1.234567 | silence_duration: 1.111111
[silencedetect @ 0x7f001] silence_start: 5.000000
[silencedetect @ 0x7f001] silence_end: 6.500000 | silence_duration: 1.500000
"#;

    const SPECTRAL_TEXT: &str = r#"
frame:0   pts:0     pts_time:0
lavfi.aspectralstats.1.mean=0.001234
lavfi.aspectralstats.1.variance=0.000056
lavfi.aspectralstats.1.centroid=1234.5
lavfi.aspectralstats.2.mean=0.002345
lavfi.aspectralstats.2.variance=0.000078
"#;

    const BLACKDETECT_TEXT: &str = r#"
[blackdetect @ 0x7f001] black_start:0.123 black_end:1.234 black_duration:1.111
[blackdetect @ 0x7f001] black_start:5.000 black_end:6.500 black_duration:1.500
"#;

    const FREEZEDETECT_TEXT: &str = r#"
[freezedetect @ 0x7f001] lavfi.freezedetect.freeze_start: 1.234
[freezedetect @ 0x7f001] lavfi.freezedetect.freeze_end: 5.678
[freezedetect @ 0x7f001] lavfi.freezedetect.freeze_duration: 4.444
"#;

    // -- Loudness tests --

    #[test]
    fn test_parse_loudness_input_i_field() {
        let r = py_parse_loudness_report(LOUDNORM_JSON_INPUT_I).unwrap();
        assert!((r.integrated_lufs - (-16.23)).abs() < 1e-9);
        assert!((r.lra - 4.20).abs() < 1e-9);
        assert!((r.true_peak_dbtp - (-1.09)).abs() < 1e-9);
    }

    #[test]
    fn test_parse_loudness_integrated_loudness_field() {
        let r = py_parse_loudness_report(LOUDNORM_JSON_INTEGRATED_LOUDNESS).unwrap();
        assert!((r.integrated_lufs - (-14.82)).abs() < 1e-9);
        assert!((r.lra - 9.10).abs() < 1e-9);
        assert!((r.true_peak_dbtp - (-0.84)).abs() < 1e-9);
    }

    #[test]
    fn test_parse_loudness_empty_returns_err() {
        assert!(py_parse_loudness_report("").is_err());
    }

    #[test]
    fn test_parse_loudness_missing_lra_returns_err() {
        let json = r#"{"input_i": "-16.0", "input_tp": "-1.0"}"#;
        assert!(py_parse_loudness_report(json).is_err());
    }

    // -- Peak tests --

    #[test]
    fn test_parse_peak_astats_overall_section() {
        // Verifies the Overall section is used (not the Channel 1 peak of -3.200)
        let r = py_parse_peak_report(ASTATS_TEXT).unwrap();
        assert!((r.peak_level - (-0.003)).abs() < 1e-9);
        assert_eq!(r.clipped_samples, 12);
    }

    #[test]
    fn test_parse_peak_volumedetect() {
        let r = py_parse_peak_report(VOLUMEDETECT_TEXT).unwrap();
        assert!((r.peak_level - (-0.5)).abs() < 1e-9);
        assert_eq!(r.clipped_samples, 0);
    }

    #[test]
    fn test_parse_peak_empty_returns_err() {
        assert!(py_parse_peak_report("").is_err());
    }

    // -- Silence tests --

    #[test]
    fn test_parse_silence_multi_region() {
        let r = py_parse_silence_report(SILENCE_TEXT).unwrap();
        assert_eq!(r.regions.len(), 2);
        assert!((r.regions[0].start - 0.123456).abs() < 1e-6);
        assert!((r.regions[0].end - 1.234567).abs() < 1e-6);
        assert!((r.regions[1].start - 5.0).abs() < 1e-6);
        assert!((r.regions[1].end - 6.5).abs() < 1e-6);
    }

    #[test]
    fn test_parse_silence_empty_input() {
        // Empty input yields empty regions (no error)
        let r = py_parse_silence_report("").unwrap();
        assert!(r.regions.is_empty());
    }

    #[test]
    fn test_parse_silence_trailing_start_gets_max_end() {
        let text = "[silencedetect @ 0x7f] silence_start: 3.0";
        let r = py_parse_silence_report(text).unwrap();
        assert_eq!(r.regions.len(), 1);
        assert!((r.regions[0].start - 3.0).abs() < 1e-9);
        assert_eq!(r.regions[0].end, f64::MAX);
    }

    // -- Spectral tests --

    #[test]
    fn test_parse_spectral_two_channels() {
        let r = py_parse_spectral_report(SPECTRAL_TEXT).unwrap();
        assert_eq!(r.channel_count, 2);
        assert_eq!(r.channel_means.len(), 2);
        assert!((r.channel_means[0] - 0.001234).abs() < 1e-9);
        assert!((r.channel_means[1] - 0.002345).abs() < 1e-9);
    }

    #[test]
    fn test_parse_spectral_empty_returns_err() {
        assert!(py_parse_spectral_report("").is_err());
    }

    #[test]
    fn test_parse_spectral_no_mean_lines_returns_err() {
        let text = "frame:0   pts:0     pts_time:0\nlavfi.aspectralstats.1.variance=0.001\n";
        assert!(py_parse_spectral_report(text).is_err());
    }

    // -- Video defect tests --

    #[test]
    fn test_parse_video_defect_blackdetect() {
        let r = py_parse_video_defect_report(BLACKDETECT_TEXT).unwrap();
        assert_eq!(r.black_regions.len(), 2);
        assert!((r.black_regions[0].start - 0.123).abs() < 1e-9);
        assert!((r.black_regions[0].end - 1.234).abs() < 1e-9);
        assert!((r.black_regions[1].start - 5.0).abs() < 1e-9);
        assert!((r.black_regions[1].end - 6.5).abs() < 1e-9);
        assert!(r.freeze_regions.is_empty());
    }

    #[test]
    fn test_parse_video_defect_freezedetect() {
        let r = py_parse_video_defect_report(FREEZEDETECT_TEXT).unwrap();
        assert!(r.black_regions.is_empty());
        assert_eq!(r.freeze_regions.len(), 1);
        assert!((r.freeze_regions[0].start - 1.234).abs() < 1e-9);
        assert!((r.freeze_regions[0].end - 5.678).abs() < 1e-9);
    }

    #[test]
    fn test_parse_video_defect_empty_input() {
        let r = py_parse_video_defect_report("").unwrap();
        assert!(r.black_regions.is_empty());
        assert!(r.freeze_regions.is_empty());
    }

    #[test]
    fn test_parse_video_defect_mixed_output() {
        let mixed = format!("{}{}", BLACKDETECT_TEXT, FREEZEDETECT_TEXT);
        let r = py_parse_video_defect_report(&mixed).unwrap();
        assert_eq!(r.black_regions.len(), 2);
        assert_eq!(r.freeze_regions.len(), 1);
    }
}

// ---------------------------------------------------------------------------
// Property-based tests (no-panic invariant)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        /// BL-423-AC-5: parse_loudness_report never panics on arbitrary input.
        #[test]
        fn no_panic_loudness(s in ".*") {
            let _ = py_parse_loudness_report(&s);
        }

        /// BL-423-AC-5: parse_peak_report never panics on arbitrary input.
        #[test]
        fn no_panic_peak(s in ".*") {
            let _ = py_parse_peak_report(&s);
        }

        /// BL-423-AC-5: parse_silence_report never panics on arbitrary input.
        #[test]
        fn no_panic_silence(s in ".*") {
            let _ = py_parse_silence_report(&s);
        }

        /// BL-423-AC-5: parse_spectral_report never panics on arbitrary input.
        #[test]
        fn no_panic_spectral(s in ".*") {
            let _ = py_parse_spectral_report(&s);
        }

        /// BL-423-AC-5: parse_video_defect_report never panics on arbitrary input.
        #[test]
        fn no_panic_video_defect(s in ".*") {
            let _ = py_parse_video_defect_report(&s);
        }
    }
}
