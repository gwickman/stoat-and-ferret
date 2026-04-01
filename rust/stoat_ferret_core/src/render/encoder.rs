//! Hardware encoder detection, selection, and encoding argument building.
//!
//! Parses FFmpeg `-encoders` output to detect available video encoders,
//! classifies them as hardware or software based on the `{codec}_{platform}`
//! naming pattern, selects the optimal encoder via a fallback chain, and
//! builds encoder-specific FFmpeg arguments for different quality presets.

use pyo3::prelude::*;
use regex::Regex;
use std::sync::LazyLock;

/// Regex for parsing FFmpeg `-encoders` output data lines.
///
/// Captures: (1) flags, (2) encoder name, (3) description, (4) optional codec.
static ENCODER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s([VAS][F.][S.][X.][B.][D.])\s(\S+)\s+(.+?)(?:\s+\(codec (\S+)\))?$").unwrap()
});

/// Known hardware encoder platform suffixes.
const HARDWARE_PLATFORMS: &[(&str, EncoderType)] = &[
    ("nvenc", EncoderType::Nvenc),
    ("qsv", EncoderType::Qsv),
    ("vaapi", EncoderType::Vaapi),
    ("amf", EncoderType::Amf),
    ("mf", EncoderType::Mf),
];

/// Fallback priority order for encoder selection (highest priority first).
const FALLBACK_ORDER: &[EncoderType] = &[
    EncoderType::Nvenc,
    EncoderType::Qsv,
    EncoderType::Vaapi,
    EncoderType::Amf,
    EncoderType::Mf,
    EncoderType::Software,
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// Type of hardware acceleration used by an encoder.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EncoderType {
    /// Software (CPU) encoding.
    Software = 0,
    /// NVIDIA NVENC hardware encoding.
    Nvenc = 1,
    /// Intel Quick Sync Video hardware encoding.
    Qsv = 2,
    /// Video Acceleration API (Linux) hardware encoding.
    Vaapi = 3,
    /// AMD Advanced Media Framework hardware encoding.
    Amf = 4,
    /// Microsoft Media Foundation hardware encoding.
    Mf = 5,
}

/// Quality preset for encoding output.
///
/// Maps to encoder-specific parameters (CRF, CQ, QP, etc.) rather than
/// FFmpeg's built-in preset names.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QualityPreset {
    /// Fast encoding, lower quality, smaller file size.
    Draft = 0,
    /// Balanced encoding speed and quality.
    Standard = 1,
    /// Slow encoding, highest quality, larger file size.
    High = 2,
}

/// Information about a detected video encoder.
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct EncoderInfo {
    /// Encoder name as reported by FFmpeg (e.g., "h264_nvenc", "libx264").
    #[pyo3(get)]
    pub name: String,
    /// Codec identifier (e.g., "h264", "hevc", "av1").
    #[pyo3(get)]
    pub codec: String,
    /// Whether this is a hardware-accelerated encoder.
    #[pyo3(get)]
    pub is_hardware: bool,
    /// Type of hardware acceleration.
    #[pyo3(get)]
    pub encoder_type: EncoderType,
    /// Encoder description from FFmpeg output.
    #[pyo3(get)]
    pub description: String,
}

#[pymethods]
impl EncoderInfo {
    /// Creates a new EncoderInfo.
    ///
    /// Args:
    ///     name: Encoder name (e.g., "h264_nvenc").
    ///     codec: Codec identifier (e.g., "h264").
    ///     is_hardware: Whether this is hardware-accelerated.
    ///     encoder_type: Type of hardware acceleration.
    ///     description: Encoder description.
    #[new]
    pub fn py_new(
        name: String,
        codec: String,
        is_hardware: bool,
        encoder_type: EncoderType,
        description: String,
    ) -> Self {
        Self {
            name,
            codec,
            is_hardware,
            encoder_type,
            description,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "EncoderInfo(name={}, codec={}, hw={})",
            self.name, self.codec, self.is_hardware
        )
    }
}

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

/// Detects available video encoders by parsing FFmpeg `-encoders` output.
///
/// Parses each line, filters to video encoders only, and classifies each
/// as hardware or software based on the `{codec}_{platform}` naming pattern.
///
/// Args:
///     ffmpeg_output: Complete output from `ffmpeg -encoders`.
///
/// Returns:
///     List of detected video encoders with classification.
#[pyfunction]
#[pyo3(name = "detect_hardware_encoders")]
pub fn py_detect_hardware_encoders(ffmpeg_output: &str) -> Vec<EncoderInfo> {
    detect_hardware_encoders(ffmpeg_output)
}

/// Detects available video encoders from FFmpeg `-encoders` output.
pub fn detect_hardware_encoders(ffmpeg_output: &str) -> Vec<EncoderInfo> {
    let mut encoders = Vec::new();
    // FFmpeg output has a header section ending with "------".
    // If we find it, skip everything up to and including that line.
    let has_header = ffmpeg_output
        .lines()
        .any(|l| l.trim_start().starts_with("------"));
    let mut past_header = !has_header;
    for line in ffmpeg_output.lines() {
        if !past_header {
            if line.trim_start().starts_with("------") {
                past_header = true;
            }
            continue;
        }
        if let Some(caps) = ENCODER_RE.captures(line) {
            let flags = caps.get(1).unwrap().as_str();
            // Only process video encoders (type flag = 'V')
            if !flags.starts_with('V') {
                continue;
            }
            let name = caps.get(2).unwrap().as_str().to_string();
            let description = caps.get(3).unwrap().as_str().trim().to_string();
            // Use explicit codec suffix if present, otherwise encoder name is the codec
            let codec = caps
                .get(4)
                .map(|m| m.as_str().to_string())
                .unwrap_or_else(|| name.clone());

            let (is_hardware, encoder_type) = classify_encoder(&name);

            encoders.push(EncoderInfo {
                name,
                codec,
                is_hardware,
                encoder_type,
                description,
            });
        }
    }
    encoders
}

/// Classifies an encoder as hardware or software by checking for known
/// platform suffixes in the encoder name.
fn classify_encoder(name: &str) -> (bool, EncoderType) {
    for (suffix, etype) in HARDWARE_PLATFORMS {
        if name.ends_with(&format!("_{suffix}")) {
            return (true, *etype);
        }
    }
    (false, EncoderType::Software)
}

// ---------------------------------------------------------------------------
// Selection
// ---------------------------------------------------------------------------

/// Selects the best encoder for a codec from available encoders.
///
/// Follows the fallback chain: nvenc → qsv → vaapi → amf → mf → software.
/// Always returns a valid encoder; synthesises a default software encoder
/// if no matching encoder is found in the available list.
///
/// Args:
///     available: List of detected encoders.
///     codec: Target codec (e.g., "h264", "hevc").
///
/// Returns:
///     The best available encoder for the requested codec.
#[pyfunction]
#[pyo3(name = "select_encoder")]
pub fn py_select_encoder(available: Vec<EncoderInfo>, codec: &str) -> EncoderInfo {
    select_encoder(&available, codec)
}

/// Selects the best encoder for a codec from available encoders.
pub fn select_encoder(available: &[EncoderInfo], codec: &str) -> EncoderInfo {
    let matching: Vec<&EncoderInfo> = available.iter().filter(|e| e.codec == codec).collect();

    // Try each type in fallback priority order
    for etype in FALLBACK_ORDER {
        if let Some(encoder) = matching.iter().find(|e| e.encoder_type == *etype) {
            return (*encoder).clone();
        }
    }

    // Ultimate fallback: synthesise a default software encoder
    let default_name = match codec {
        "h264" => "libx264",
        "hevc" | "h265" => "libx265",
        "vp9" => "libvpx-vp9",
        "av1" => "libaom-av1",
        _ => "libx264",
    };
    EncoderInfo {
        name: default_name.to_string(),
        codec: codec.to_string(),
        is_hardware: false,
        encoder_type: EncoderType::Software,
        description: format!("Default {codec} software encoder"),
    }
}

// ---------------------------------------------------------------------------
// Argument building
// ---------------------------------------------------------------------------

/// Builds FFmpeg encoding arguments for an encoder and quality preset.
///
/// Returns a list of FFmpeg command-line arguments appropriate for the
/// encoder type and quality level (codec flag, quality params, preset).
///
/// Args:
///     encoder: The encoder to build arguments for.
///     quality: The target quality preset.
///
/// Returns:
///     List of FFmpeg CLI argument strings.
#[pyfunction]
#[pyo3(name = "build_encoding_args")]
pub fn py_build_encoding_args(encoder: &EncoderInfo, quality: &QualityPreset) -> Vec<String> {
    build_encoding_args(encoder, quality)
}

/// Builds FFmpeg encoding arguments for an encoder and quality preset.
pub fn build_encoding_args(encoder: &EncoderInfo, quality: &QualityPreset) -> Vec<String> {
    let mut args = vec!["-c:v".to_string(), encoder.name.clone()];

    match encoder.encoder_type {
        EncoderType::Software => {
            let (preset, crf) = match quality {
                QualityPreset::Draft => ("veryfast", "28"),
                QualityPreset::Standard => ("medium", "23"),
                QualityPreset::High => ("slow", "18"),
            };
            args.extend(["-preset".into(), preset.into(), "-crf".into(), crf.into()]);
        }
        EncoderType::Nvenc => {
            let (preset, cq) = match quality {
                QualityPreset::Draft => ("p1", "32"),
                QualityPreset::Standard => ("p4", "24"),
                QualityPreset::High => ("p7", "18"),
            };
            args.extend([
                "-preset".into(),
                preset.into(),
                "-rc".into(),
                "vbr".into(),
                "-cq".into(),
                cq.into(),
            ]);
        }
        EncoderType::Qsv => {
            let (preset, gq) = match quality {
                QualityPreset::Draft => ("veryfast", "28"),
                QualityPreset::Standard => ("medium", "23"),
                QualityPreset::High => ("veryslow", "18"),
            };
            args.extend([
                "-preset".into(),
                preset.into(),
                "-global_quality".into(),
                gq.into(),
            ]);
        }
        EncoderType::Vaapi => {
            let qp = match quality {
                QualityPreset::Draft => "30",
                QualityPreset::Standard => "24",
                QualityPreset::High => "18",
            };
            args.extend(["-qp".into(), qp.into()]);
        }
        EncoderType::Amf => {
            let (amf_quality, qp) = match quality {
                QualityPreset::Draft => ("speed", "28"),
                QualityPreset::Standard => ("balanced", "23"),
                QualityPreset::High => ("quality", "18"),
            };
            args.extend([
                "-quality".into(),
                amf_quality.into(),
                "-qp_i".into(),
                qp.into(),
                "-qp_p".into(),
                qp.into(),
            ]);
        }
        EncoderType::Mf => {
            let rate = match quality {
                QualityPreset::Draft => "1000000",
                QualityPreset::Standard => "5000000",
                QualityPreset::High => "10000000",
            };
            args.extend(["-b:v".into(), rate.into()]);
        }
    }

    args
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- Fixtures --

    /// Representative FFmpeg `-encoders` output fixture.
    /// Covers video (software + hardware), audio, and subtitle encoders.
    const FFMPEG_ENCODERS_FIXTURE: &str = "\
Encoders:
 V..... = Video
 A..... = Audio
 S..... = Subtitle
 .F.... = Frame-level multithreading
 ..S... = Slice-level multithreading
 ...X.. = Codec is experimental
 ....B. = Supports draw_horiz_band
 .....D = Supports direct rendering method 1
 ------
 V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V..... libx264rgb           libx264rgb H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 RGB (codec h264)
 V..... libx265              libx265 H.265 / HEVC (codec hevc)
 V..... libvpx               libvpx VP8 (codec vp8)
 V..... libvpx-vp9           libvpx-vp9 (codec vp9)
 V..... libaom-av1           libaom-av1 (codec av1)
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V..... hevc_nvenc           NVIDIA NVENC hevc encoder (codec hevc)
 V..... av1_nvenc            NVIDIA NVENC av1 encoder (codec av1)
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
 V..... hevc_qsv             HEVC (Intel Quick Sync Video acceleration) (codec hevc)
 V..... av1_qsv              AV1 (Intel Quick Sync Video acceleration) (codec av1)
 V..... h264_vaapi           H.264/AVC (VAAPI) (codec h264)
 V..... hevc_vaapi           H.265/HEVC (VAAPI) (codec hevc)
 V..... av1_vaapi            AV1 (VAAPI) (codec av1)
 V..... h264_amf             AMD AMF H.264 Encoder (codec h264)
 V..... hevc_amf             AMD AMF HEVC Encoder (codec hevc)
 V..... av1_amf              AMD AMF AV1 Encoder (codec av1)
 V..... h264_mf              H264 via MediaFoundation (codec h264)
 V..... hevc_mf              HEVC via MediaFoundation (codec hevc)
 V..... prores_ks            Apple ProRes (codec prores)
 A..... aac                  AAC (Advanced Audio Coding)
 A..... libmp3lame           libmp3lame MP3 (MPEG audio layer 3) (codec mp3)
 A..... libopus              libopus Opus (codec opus)
 A..... libvorbis            libvorbis (codec vorbis)
 S..... srt                  SubRip subtitle (codec subrip)
 S..... ass                  ASS (Advanced SubStation Alpha) subtitle";

    // -- detect_hardware_encoders tests --

    #[test]
    fn test_detects_all_video_encoders() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        // 6 software + 15 hardware = 21 video encoders
        assert_eq!(encoders.len(), 21);
        // All should be video (no audio/subtitle)
        assert!(encoders
            .iter()
            .all(|e| !e.name.starts_with("aac") && !e.name.starts_with("lib")
                || e.codec == "h264"
                || e.codec == "hevc"
                || e.codec == "vp8"
                || e.codec == "vp9"
                || e.codec == "av1"
                || e.codec == "prores"));
    }

    #[test]
    fn test_identifies_hardware_encoders() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let hw: Vec<_> = encoders.iter().filter(|e| e.is_hardware).collect();
        // h264: nvenc,qsv,vaapi,amf,mf; hevc: nvenc,qsv,vaapi,amf,mf; av1: nvenc,qsv,vaapi,amf = 14
        assert_eq!(hw.len(), 14);
    }

    #[test]
    fn test_identifies_software_encoders() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let sw: Vec<_> = encoders.iter().filter(|e| !e.is_hardware).collect();
        // libx264, libx264rgb, libx265, libvpx, libvpx-vp9, libaom-av1, prores_ks = 7
        // Wait, prores_ks doesn't match any hardware suffix. It ends with _ks, not a known platform.
        assert_eq!(sw.len(), 7);
    }

    #[test]
    fn test_hardware_encoder_types() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let nvenc: Vec<_> = encoders
            .iter()
            .filter(|e| e.encoder_type == EncoderType::Nvenc)
            .collect();
        assert_eq!(nvenc.len(), 3);
        assert!(nvenc.iter().all(|e| e.name.ends_with("_nvenc")));

        let qsv: Vec<_> = encoders
            .iter()
            .filter(|e| e.encoder_type == EncoderType::Qsv)
            .collect();
        assert_eq!(qsv.len(), 3);

        let vaapi: Vec<_> = encoders
            .iter()
            .filter(|e| e.encoder_type == EncoderType::Vaapi)
            .collect();
        assert_eq!(vaapi.len(), 3);

        let amf: Vec<_> = encoders
            .iter()
            .filter(|e| e.encoder_type == EncoderType::Amf)
            .collect();
        assert_eq!(amf.len(), 3);

        let mf: Vec<_> = encoders
            .iter()
            .filter(|e| e.encoder_type == EncoderType::Mf)
            .collect();
        assert_eq!(mf.len(), 2); // h264_mf, hevc_mf (no av1_mf in fixture)
    }

    #[test]
    fn test_codec_parsed_from_suffix() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let nvenc = encoders.iter().find(|e| e.name == "h264_nvenc").unwrap();
        assert_eq!(nvenc.codec, "h264");

        let hevc = encoders.iter().find(|e| e.name == "hevc_nvenc").unwrap();
        assert_eq!(hevc.codec, "hevc");
    }

    #[test]
    fn test_codec_without_suffix_uses_name() {
        // The "aac" encoder has no (codec ...) suffix, but it's audio so filtered.
        // Test with a synthetic video encoder that has no codec suffix.
        let input = " V..... rawvideo             raw video";
        let encoders = detect_hardware_encoders(input);
        assert_eq!(encoders.len(), 1);
        assert_eq!(encoders[0].codec, "rawvideo");
    }

    #[test]
    fn test_description_parsed() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let nvenc = encoders.iter().find(|e| e.name == "h264_nvenc").unwrap();
        assert_eq!(nvenc.description, "NVIDIA NVENC H.264 encoder");
    }

    #[test]
    fn test_empty_input() {
        let encoders = detect_hardware_encoders("");
        assert!(encoders.is_empty());
    }

    #[test]
    fn test_header_only_input() {
        let input = "Encoders:\n ------\n";
        let encoders = detect_hardware_encoders(input);
        assert!(encoders.is_empty());
    }

    #[test]
    fn test_prores_is_software() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let prores = encoders.iter().find(|e| e.name == "prores_ks").unwrap();
        assert!(!prores.is_hardware);
        assert_eq!(prores.encoder_type, EncoderType::Software);
        assert_eq!(prores.codec, "prores");
    }

    // -- select_encoder tests --

    #[test]
    fn test_selects_nvenc_first() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let selected = select_encoder(&encoders, "h264");
        assert_eq!(selected.name, "h264_nvenc");
        assert_eq!(selected.encoder_type, EncoderType::Nvenc);
    }

    #[test]
    fn test_fallback_to_qsv_without_nvenc() {
        let encoders: Vec<EncoderInfo> = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE)
            .into_iter()
            .filter(|e| e.encoder_type != EncoderType::Nvenc)
            .collect();
        let selected = select_encoder(&encoders, "h264");
        assert_eq!(selected.name, "h264_qsv");
    }

    #[test]
    fn test_fallback_to_software() {
        let encoders: Vec<EncoderInfo> = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE)
            .into_iter()
            .filter(|e| !e.is_hardware)
            .collect();
        let selected = select_encoder(&encoders, "h264");
        assert_eq!(selected.name, "libx264");
        assert_eq!(selected.encoder_type, EncoderType::Software);
    }

    #[test]
    fn test_fallback_order() {
        // Remove types one at a time to verify the full chain
        let all = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);

        // With all: nvenc wins
        assert_eq!(
            select_encoder(&all, "h264").encoder_type,
            EncoderType::Nvenc
        );

        // Without nvenc: qsv wins
        let no_nvenc: Vec<_> = all
            .iter()
            .filter(|e| e.encoder_type != EncoderType::Nvenc)
            .cloned()
            .collect();
        assert_eq!(
            select_encoder(&no_nvenc, "h264").encoder_type,
            EncoderType::Qsv
        );

        // Without nvenc+qsv: vaapi wins
        let no_nq: Vec<_> = no_nvenc
            .iter()
            .filter(|e| e.encoder_type != EncoderType::Qsv)
            .cloned()
            .collect();
        assert_eq!(
            select_encoder(&no_nq, "h264").encoder_type,
            EncoderType::Vaapi
        );

        // Without nvenc+qsv+vaapi: amf wins
        let no_nqv: Vec<_> = no_nq
            .iter()
            .filter(|e| e.encoder_type != EncoderType::Vaapi)
            .cloned()
            .collect();
        assert_eq!(
            select_encoder(&no_nqv, "h264").encoder_type,
            EncoderType::Amf
        );

        // Without nvenc+qsv+vaapi+amf: mf wins
        let no_nqva: Vec<_> = no_nqv
            .iter()
            .filter(|e| e.encoder_type != EncoderType::Amf)
            .cloned()
            .collect();
        assert_eq!(
            select_encoder(&no_nqva, "h264").encoder_type,
            EncoderType::Mf
        );

        // Without all hardware: software wins
        let sw_only: Vec<_> = no_nqva
            .iter()
            .filter(|e| e.encoder_type != EncoderType::Mf)
            .cloned()
            .collect();
        assert_eq!(
            select_encoder(&sw_only, "h264").encoder_type,
            EncoderType::Software
        );
    }

    #[test]
    fn test_select_unknown_codec_returns_default() {
        let encoders = detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
        let selected = select_encoder(&encoders, "unknown");
        assert_eq!(selected.name, "libx264");
        assert!(!selected.is_hardware);
    }

    #[test]
    fn test_select_empty_available() {
        let selected = select_encoder(&[], "h264");
        assert_eq!(selected.name, "libx264");
        assert_eq!(selected.encoder_type, EncoderType::Software);
    }

    #[test]
    fn test_select_hevc_default() {
        let selected = select_encoder(&[], "hevc");
        assert_eq!(selected.name, "libx265");
    }

    #[test]
    fn test_select_av1_default() {
        let selected = select_encoder(&[], "av1");
        assert_eq!(selected.name, "libaom-av1");
    }

    // -- build_encoding_args tests --

    #[test]
    fn test_software_draft_args() {
        let encoder = EncoderInfo {
            name: "libx264".into(),
            codec: "h264".into(),
            is_hardware: false,
            encoder_type: EncoderType::Software,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::Draft);
        assert_eq!(
            args,
            vec!["-c:v", "libx264", "-preset", "veryfast", "-crf", "28"]
        );
    }

    #[test]
    fn test_software_standard_args() {
        let encoder = EncoderInfo {
            name: "libx264".into(),
            codec: "h264".into(),
            is_hardware: false,
            encoder_type: EncoderType::Software,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::Standard);
        assert_eq!(
            args,
            vec!["-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        );
    }

    #[test]
    fn test_software_high_args() {
        let encoder = EncoderInfo {
            name: "libx264".into(),
            codec: "h264".into(),
            is_hardware: false,
            encoder_type: EncoderType::Software,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::High);
        assert_eq!(
            args,
            vec!["-c:v", "libx264", "-preset", "slow", "-crf", "18"]
        );
    }

    #[test]
    fn test_nvenc_args() {
        let encoder = EncoderInfo {
            name: "h264_nvenc".into(),
            codec: "h264".into(),
            is_hardware: true,
            encoder_type: EncoderType::Nvenc,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::Standard);
        assert_eq!(
            args,
            vec![
                "-c:v",
                "h264_nvenc",
                "-preset",
                "p4",
                "-rc",
                "vbr",
                "-cq",
                "24"
            ]
        );
    }

    #[test]
    fn test_qsv_args() {
        let encoder = EncoderInfo {
            name: "h264_qsv".into(),
            codec: "h264".into(),
            is_hardware: true,
            encoder_type: EncoderType::Qsv,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::High);
        assert_eq!(
            args,
            vec![
                "-c:v",
                "h264_qsv",
                "-preset",
                "veryslow",
                "-global_quality",
                "18"
            ]
        );
    }

    #[test]
    fn test_vaapi_args() {
        let encoder = EncoderInfo {
            name: "h264_vaapi".into(),
            codec: "h264".into(),
            is_hardware: true,
            encoder_type: EncoderType::Vaapi,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::Draft);
        assert_eq!(args, vec!["-c:v", "h264_vaapi", "-qp", "30"]);
    }

    #[test]
    fn test_amf_args() {
        let encoder = EncoderInfo {
            name: "h264_amf".into(),
            codec: "h264".into(),
            is_hardware: true,
            encoder_type: EncoderType::Amf,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::Standard);
        assert_eq!(
            args,
            vec!["-c:v", "h264_amf", "-quality", "balanced", "-qp_i", "23", "-qp_p", "23"]
        );
    }

    #[test]
    fn test_mf_args() {
        let encoder = EncoderInfo {
            name: "h264_mf".into(),
            codec: "h264".into(),
            is_hardware: true,
            encoder_type: EncoderType::Mf,
            description: "".into(),
        };
        let args = build_encoding_args(&encoder, &QualityPreset::High);
        assert_eq!(args, vec!["-c:v", "h264_mf", "-b:v", "10000000"]);
    }

    #[test]
    fn test_all_presets_produce_nonempty_args() {
        let encoder = EncoderInfo {
            name: "libx264".into(),
            codec: "h264".into(),
            is_hardware: false,
            encoder_type: EncoderType::Software,
            description: "".into(),
        };
        for quality in [
            QualityPreset::Draft,
            QualityPreset::Standard,
            QualityPreset::High,
        ] {
            let args = build_encoding_args(&encoder, &quality);
            assert!(!args.is_empty());
            assert_eq!(args[0], "-c:v");
            assert_eq!(args[1], "libx264");
        }
    }

    #[test]
    fn test_all_encoder_types_produce_args() {
        let types = [
            ("libx264", EncoderType::Software, false),
            ("h264_nvenc", EncoderType::Nvenc, true),
            ("h264_qsv", EncoderType::Qsv, true),
            ("h264_vaapi", EncoderType::Vaapi, true),
            ("h264_amf", EncoderType::Amf, true),
            ("h264_mf", EncoderType::Mf, true),
        ];
        for (name, etype, hw) in types {
            let encoder = EncoderInfo {
                name: name.into(),
                codec: "h264".into(),
                is_hardware: hw,
                encoder_type: etype,
                description: "".into(),
            };
            let args = build_encoding_args(&encoder, &QualityPreset::Standard);
            assert!(args.len() >= 2, "args too short for {name}");
            assert_eq!(args[0], "-c:v");
            assert_eq!(args[1], name);
        }
    }

    // -- Contract tests (NFR-002: handles 230+ encoder lines) --

    #[test]
    fn test_handles_large_encoder_list() {
        // Generate 230+ encoder lines to verify no performance degradation
        let mut lines = String::from("Encoders:\n ------\n");
        for i in 0..230 {
            lines.push_str(&format!(
                " V..... encoder_{i:03}           Test encoder {i} (codec h264)\n"
            ));
        }
        // Add some audio/subtitle lines too
        for i in 0..20 {
            lines.push_str(&format!(
                " A..... audio_{i:03}              Audio encoder {i} (codec aac)\n"
            ));
        }
        let encoders = detect_hardware_encoders(&lines);
        assert_eq!(encoders.len(), 230);
    }

    #[test]
    fn test_8char_prefix_schema() {
        // Verify the 8-char fixed-width prefix is parsed correctly
        // Position: " VFSXBD " (space, type, frame_mt, slice_mt, experimental, draw, direct, space)
        let lines = vec![
            " VF.... libx264              test (codec h264)", // frame_mt set
            " V.S... libx265              test (codec hevc)", // slice_mt set
            " V..X.. test_exp             test (codec h264)", // experimental set
            " V...B. test_band            test (codec h264)", // draw_horiz set
            " V....D test_direct          test (codec h264)", // direct_render set
            " VFSXBD test_all             test (codec h264)", // all flags set
        ];
        let input = lines.join("\n");
        let encoders = detect_hardware_encoders(&input);
        assert_eq!(encoders.len(), 6);
    }

    #[test]
    fn test_windows_mf_encoders() {
        // Verify h264_mf and hevc_mf (Windows-only) are detected as hardware
        let input = " V..... h264_mf              H264 via MediaFoundation (codec h264)\n V..... hevc_mf              HEVC via MediaFoundation (codec hevc)";
        let encoders = detect_hardware_encoders(input);
        assert_eq!(encoders.len(), 2);
        assert!(encoders.iter().all(|e| e.is_hardware));
        assert!(encoders.iter().all(|e| e.encoder_type == EncoderType::Mf));
    }

    // -- PyO3 binding tests --

    #[test]
    fn test_pyo3_detect_hardware_encoders() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = py_detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
            assert_eq!(result.len(), 21);
            // Verify they can be converted to Python objects
            let py_list = pyo3::types::PyList::new(
                py,
                result.iter().map(|e| e.clone().into_pyobject(py).unwrap()),
            )
            .unwrap();
            assert_eq!(py_list.len(), 21);
        });
    }

    #[test]
    fn test_pyo3_select_encoder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let available = py_detect_hardware_encoders(FFMPEG_ENCODERS_FIXTURE);
            let selected = py_select_encoder(available, "h264");
            assert_eq!(selected.name, "h264_nvenc");
        });
    }

    #[test]
    fn test_pyo3_build_encoding_args() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let encoder = EncoderInfo {
                name: "libx264".into(),
                codec: "h264".into(),
                is_hardware: false,
                encoder_type: EncoderType::Software,
                description: "".into(),
            };
            let args = py_build_encoding_args(&encoder, &QualityPreset::Standard);
            assert_eq!(args[0], "-c:v");
            assert_eq!(args[1], "libx264");
        });
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    /// Strategy that generates an arbitrary set of encoder types for a codec.
    fn encoder_availability() -> impl Strategy<Value = Vec<EncoderInfo>> {
        prop::collection::vec(
            (
                prop::sample::select(vec![
                    EncoderType::Software,
                    EncoderType::Nvenc,
                    EncoderType::Qsv,
                    EncoderType::Vaapi,
                    EncoderType::Amf,
                    EncoderType::Mf,
                ]),
                prop::bool::ANY,
            ),
            0..=6,
        )
        .prop_map(|types| {
            types
                .into_iter()
                .enumerate()
                .map(|(i, (etype, _))| {
                    let (name, hw) = match etype {
                        EncoderType::Software => ("libx264".to_string(), false),
                        EncoderType::Nvenc => ("h264_nvenc".to_string(), true),
                        EncoderType::Qsv => ("h264_qsv".to_string(), true),
                        EncoderType::Vaapi => ("h264_vaapi".to_string(), true),
                        EncoderType::Amf => ("h264_amf".to_string(), true),
                        EncoderType::Mf => ("h264_mf".to_string(), true),
                    };
                    EncoderInfo {
                        name: format!("{name}_{i}"),
                        codec: "h264".to_string(),
                        is_hardware: hw,
                        encoder_type: etype,
                        description: "test".to_string(),
                    }
                })
                .collect()
        })
    }

    fn quality_preset_strategy() -> impl Strategy<Value = QualityPreset> {
        prop::sample::select(vec![
            QualityPreset::Draft,
            QualityPreset::Standard,
            QualityPreset::High,
        ])
    }

    proptest! {
        /// FR-004: select_encoder always returns a valid encoder for any availability set.
        #[test]
        fn select_encoder_never_panics(available in encoder_availability()) {
            let result = select_encoder(&available, "h264");
            // Must always return something
            prop_assert!(!result.name.is_empty());
            prop_assert!(!result.codec.is_empty());
        }

        /// build_encoding_args always returns non-empty args for any quality preset.
        #[test]
        fn build_encoding_args_always_nonempty(quality in quality_preset_strategy()) {
            let encoder = EncoderInfo {
                name: "libx264".into(),
                codec: "h264".into(),
                is_hardware: false,
                encoder_type: EncoderType::Software,
                description: "".into(),
            };
            let args = build_encoding_args(&encoder, &quality);
            prop_assert!(!args.is_empty());
            prop_assert_eq!(&args[0], "-c:v");
        }

        /// build_encoding_args produces non-empty args for all encoder types.
        #[test]
        fn build_encoding_args_all_types(
            etype in prop::sample::select(vec![
                EncoderType::Software,
                EncoderType::Nvenc,
                EncoderType::Qsv,
                EncoderType::Vaapi,
                EncoderType::Amf,
                EncoderType::Mf,
            ]),
            quality in quality_preset_strategy(),
        ) {
            let name = match etype {
                EncoderType::Software => "libx264",
                EncoderType::Nvenc => "h264_nvenc",
                EncoderType::Qsv => "h264_qsv",
                EncoderType::Vaapi => "h264_vaapi",
                EncoderType::Amf => "h264_amf",
                EncoderType::Mf => "h264_mf",
            };
            let encoder = EncoderInfo {
                name: name.into(),
                codec: "h264".into(),
                is_hardware: etype != EncoderType::Software,
                encoder_type: etype,
                description: "".into(),
            };
            let args = build_encoding_args(&encoder, &quality);
            prop_assert!(args.len() >= 2);
            prop_assert_eq!(&args[0], "-c:v");
            prop_assert_eq!(&args[1], name);
        }
    }
}
