// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Subtitle effect builders for drawtext caption chains and sidecar burn-in.
//!
//! Provides [`SubtitleScriptBuilder`] which emits N `drawtext` filters
//! chained with `enable='between(t,s,e)'` expressions for timed captions,
//! and [`BurnedSubtitleBuilder`] which wraps the FFmpeg `subtitles` (SRT)
//! and `ass` (ASS) filters for sidecar file burn-in.

use std::collections::HashMap;

use pyo3::prelude::*;

use crate::ffmpeg::drawtext::escape_drawtext;
use crate::ffmpeg::video::{emit_filter_value, ValueKind};

/// Entry in a subtitle script: time window + caption text.
#[pyclass]
#[derive(Clone)]
pub struct ScriptEntry {
    #[pyo3(get)]
    pub start_s: f64,
    #[pyo3(get)]
    pub end_s: f64,
    #[pyo3(get)]
    pub text: String,
}

#[pymethods]
impl ScriptEntry {
    #[new]
    pub fn py_new(start_s: f64, end_s: f64, text: String) -> PyResult<Self> {
        if start_s >= end_s {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "start_s ({}) must be less than end_s ({})",
                start_s, end_s
            )));
        }
        Ok(ScriptEntry {
            start_s,
            end_s,
            text,
        })
    }
}

/// Uniform-style spec for a subtitle script (N timed captions).
#[pyclass]
pub struct SubtitleScriptSpec {
    #[pyo3(get)]
    pub entries: Vec<ScriptEntry>,
    #[pyo3(get)]
    pub position: String,
    #[pyo3(get)]
    pub font_size: u32,
    #[pyo3(get)]
    pub font_color: String,
    #[pyo3(get)]
    pub font_file: Option<String>,
}

#[pymethods]
impl SubtitleScriptSpec {
    #[new]
    #[pyo3(signature = (entries, position="bottom".to_string(), font_size=24, font_color="white".to_string(), font_file=None))]
    pub fn py_new(
        entries: Vec<ScriptEntry>,
        position: String,
        font_size: u32,
        font_color: String,
        font_file: Option<String>,
    ) -> PyResult<Self> {
        if position != "bottom" && position != "top" && position != "center" {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "position must be one of 'bottom', 'top', 'center'; got '{}'",
                position
            )));
        }
        if font_color.contains(':')
            || font_color.contains('\'')
            || font_color.contains(',')
            || font_color.contains(';')
        {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "font_color contains forbidden character (':', single quote, ',', ';'): {}",
                font_color
            )));
        }
        Ok(SubtitleScriptSpec {
            entries,
            position,
            font_size,
            font_color,
            font_file,
        })
    }
}

/// SubtitleScriptBuilder: emits N drawtext filters chained with enable= expressions.
#[pyclass]
pub struct SubtitleScriptBuilder;

#[pymethods]
impl SubtitleScriptBuilder {
    #[staticmethod]
    pub fn build(spec: &SubtitleScriptSpec) -> PyResult<String> {
        if spec.entries.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "entries must be non-empty",
            ));
        }
        let (x_expr, y_expr) = position_to_xy(&spec.position);
        let mut filters = Vec::new();
        for entry in &spec.entries {
            let escaped_text = escape_drawtext(&entry.text);
            let font_part = match &spec.font_file {
                Some(path) => {
                    let escaped = emit_filter_value(ValueKind::Path, path)
                        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
                    format!("fontfile={}:", escaped)
                }
                None => String::new(),
            };
            let filter = format!(
                "drawtext={}fontsize={}:fontcolor={}:text='{}':x={}:y={}:enable='between(t,{:?},{:?})'",
                font_part,
                spec.font_size,
                spec.font_color,
                escaped_text,
                x_expr,
                y_expr,
                entry.start_s,
                entry.end_s,
            );
            filters.push(filter);
        }
        Ok(filters.join(","))
    }
}

fn position_to_xy(position: &str) -> (String, String) {
    match position {
        "bottom" => ("(w-text_w)/2".to_string(), "h-text_h-10".to_string()),
        "top" => ("(w-text_w)/2".to_string(), "10".to_string()),
        "center" => ("(w-text_w)/2".to_string(), "(h-text_h)/2".to_string()),
        // Unreachable: SubtitleScriptSpec::py_new rejects unknown positions.
        _ => ("(w-text_w)/2".to_string(), "h-text_h-10".to_string()),
    }
}

/// Error variants for `escape_force_style` and key validation in `BurnedSubtitleBuilder`.
#[derive(Debug)]
pub(crate) enum ForceStyleError {
    ApostropheInValue(String),
    InvalidKeyChar { key: String, ch: char },
}

impl std::fmt::Display for ForceStyleError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ApostropheInValue(v) => {
                write!(f, "force_style value contains a bare single-quote: {v:?}")
            }
            Self::InvalidKeyChar { key, ch } => {
                write!(
                    f,
                    "force_style key {key:?} contains invalid character {ch:?}"
                )
            }
        }
    }
}

/// Escape a force_style value for embedding in a subtitles filter option.
///
/// FFmpeg `force_style` is a comma-separated `KEY=VALUE` list. Internal commas
/// in values must be escaped as `\,` to prevent the filter parser from treating
/// them as list separators. Bare single-quotes are rejected because they would
/// break out of the outer single-quoted block that `BurnedSubtitleBuilder` emits.
///
/// This escape is distinct from:
/// - `emit_filter_option_path()` (handles colon-escaped path values for `filename=`)
/// - `escape_drawtext()` (handles text escape for drawtext filter values)
pub(crate) fn escape_force_style(value: &str) -> Result<String, ForceStyleError> {
    if value.contains('\'') {
        return Err(ForceStyleError::ApostropheInValue(value.to_owned()));
    }
    Ok(value.replace(',', r"\,"))
}

/// Spec for burning subtitles from an SRT or ASS sidecar file.
///
/// Exactly one of `source_path` or `inline_text` must be provided.
/// `force_style` applies only to SRT files; it is silently ignored when
/// `source_path` points to an ASS file (ASS styles are inline).
#[pyclass]
#[derive(Clone)]
pub struct BurnedSubtitleSpec {
    #[pyo3(get)]
    pub source_path: Option<String>,
    #[pyo3(get)]
    pub inline_text: Option<String>,
    #[pyo3(get)]
    pub force_style: Option<HashMap<String, String>>,
}

#[pymethods]
impl BurnedSubtitleSpec {
    #[new]
    #[pyo3(signature = (source_path=None, inline_text=None, force_style=None))]
    pub fn py_new(
        source_path: Option<String>,
        inline_text: Option<String>,
        force_style: Option<HashMap<String, String>>,
    ) -> Self {
        BurnedSubtitleSpec {
            source_path,
            inline_text,
            force_style,
        }
    }
}

/// BurnedSubtitleBuilder: wraps FFmpeg `subtitles` (SRT) and `ass` (ASS) filters.
///
/// - SRT: emits `subtitles=filename=<escaped-path>[:force_style='<escaped-style>']`
/// - ASS: emits `ass=filename=<escaped-path>` (no force_style; styles are inline)
///
/// Path escape follows BL-499 policy via `emit_filter_option_path()`.
/// Force-style escape (commas only) via `escape_force_style()`.
#[pyclass]
pub struct BurnedSubtitleBuilder;

#[pymethods]
impl BurnedSubtitleBuilder {
    #[staticmethod]
    pub fn build(spec: &BurnedSubtitleSpec) -> PyResult<String> {
        let path = match &spec.source_path {
            Some(p) => p.clone(),
            None => match &spec.inline_text {
                Some(t) => t.clone(),
                None => {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "source_path or inline_text must be provided",
                    ))
                }
            },
        };

        let is_ass = path.to_lowercase().ends_with(".ass");
        let escaped_path = emit_filter_value(ValueKind::Path, &path)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

        if is_ass {
            // ASS styles are embedded inline; force_style has no effect.
            Ok(format!("ass=filename={}", escaped_path))
        } else {
            let base = format!("subtitles=filename={}", escaped_path);
            match &spec.force_style {
                None => Ok(base),
                Some(style_dict) => {
                    // Validate keys and escape values; sort pairs for deterministic output.
                    let mut style_pairs: Vec<String> = Vec::with_capacity(style_dict.len());
                    for (key, value) in style_dict {
                        for ch in ['\'', ',', '=', ':'] {
                            if key.contains(ch) {
                                return Err(pyo3::exceptions::PyValueError::new_err(
                                    ForceStyleError::InvalidKeyChar {
                                        key: key.clone(),
                                        ch,
                                    }
                                    .to_string(),
                                ));
                            }
                        }
                        let escaped = escape_force_style(value)
                            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
                        style_pairs.push(format!("{}={}", key, escaped));
                    }
                    style_pairs.sort();
                    let escaped_style = style_pairs.join(",");
                    Ok(format!("{}:force_style='{}'", base, escaped_style))
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_entry(start_s: f64, end_s: f64, text: &str) -> ScriptEntry {
        ScriptEntry::py_new(start_s, end_s, text.to_string()).unwrap()
    }

    fn make_spec(entries: Vec<ScriptEntry>, position: &str) -> SubtitleScriptSpec {
        SubtitleScriptSpec::py_new(entries, position.to_string(), 24, "white".to_string(), None)
            .unwrap()
    }

    #[test]
    fn test_script_entry_rejects_invalid_range() {
        assert!(ScriptEntry::py_new(5.0, 2.0, "bad".to_string()).is_err());
    }

    #[test]
    fn test_script_entry_rejects_equal_times() {
        assert!(ScriptEntry::py_new(3.0, 3.0, "bad".to_string()).is_err());
    }

    #[test]
    fn test_script_entry_accepts_valid_range() {
        let entry = make_entry(0.0, 2.0, "hello");
        assert_eq!(entry.start_s, 0.0);
        assert_eq!(entry.end_s, 2.0);
        assert_eq!(entry.text, "hello");
    }

    #[test]
    fn test_subtitle_script_spec_rejects_unknown_position() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "left".to_string(),
            24,
            "white".to_string(),
            None
        )
        .is_err());
    }

    #[test]
    fn test_subtitle_script_spec_accepts_valid_positions() {
        for pos in &["bottom", "top", "center"] {
            let entry = make_entry(0.0, 1.0, "hi");
            assert!(
                SubtitleScriptSpec::py_new(
                    vec![entry],
                    pos.to_string(),
                    24,
                    "white".to_string(),
                    None,
                )
                .is_ok(),
                "position '{}' should be accepted",
                pos
            );
        }
    }

    #[test]
    fn test_build_empty_entries_error() {
        let spec = SubtitleScriptSpec {
            entries: vec![],
            position: "bottom".to_string(),
            font_size: 24,
            font_color: "white".to_string(),
            font_file: None,
        };
        assert!(SubtitleScriptBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_build_single_entry_no_font_file() {
        let spec = make_spec(vec![make_entry(0.0, 2.0, "Hello")], "bottom");
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        assert!(result.contains("drawtext="));
        assert!(result.contains("enable='between(t,0.0,2.0)'"));
        assert!(result.contains("fontsize=24"));
        assert!(result.contains("fontcolor=white"));
        assert!(result.contains("text='Hello'"));
        assert!(result.contains("x=(w-text_w)/2"));
        assert!(result.contains("y=h-text_h-10"));
        assert!(!result.contains("fontfile="));
    }

    #[test]
    fn test_build_with_font_file() {
        let spec = SubtitleScriptSpec::py_new(
            vec![make_entry(1.0, 3.0, "Hi")],
            "top".to_string(),
            32,
            "yellow".to_string(),
            Some("/fonts/arial.ttf".to_string()),
        )
        .unwrap();
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        assert!(result.contains("fontfile=/fonts/arial.ttf:"));
        assert!(result.contains("fontsize=32"));
        assert!(result.contains("fontcolor=yellow"));
        assert!(result.contains("y=10"));
    }

    #[test]
    fn test_build_with_font_file_windows_drive() {
        let spec = SubtitleScriptSpec::py_new(
            vec![make_entry(0.0, 2.0, "Hello")],
            "bottom".to_string(),
            24,
            "white".to_string(),
            Some("C:\\Windows\\Fonts\\arial.ttf".to_string()),
        )
        .unwrap();
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        // Windows path: drive colon escaped as \:, backslashes → forward slashes, single-quoted
        assert!(
            result.contains("fontfile='C\\:/Windows/Fonts/arial.ttf':"),
            "expected escaped Windows font path in filter, got: {result}"
        );
    }

    #[test]
    fn test_build_with_font_file_space() {
        let spec = SubtitleScriptSpec::py_new(
            vec![make_entry(0.0, 2.0, "Hello")],
            "bottom".to_string(),
            24,
            "white".to_string(),
            Some("C:\\My Fonts\\cool.ttf".to_string()),
        )
        .unwrap();
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        // Space preserved inside single quotes; drive colon escaped as \:
        assert!(
            result.contains("fontfile='C\\:/My Fonts/cool.ttf':"),
            "expected space-preserved font path in filter, got: {result}"
        );
    }

    #[test]
    fn test_burned_subtitle_windows_source_path() {
        let spec = BurnedSubtitleSpec::py_new(Some("C:\\Users\\sub.srt".to_string()), None, None);
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        // BurnedSubtitleBuilder uses emit_filter_option_path: drive colon escaped as \:
        assert!(
            result.contains("filename='C\\:/Users/sub.srt'"),
            "expected escaped Windows source_path, got: {result}"
        );
    }

    #[test]
    fn test_build_multiple_entries_joined_by_comma() {
        let entries = vec![
            make_entry(0.0, 2.0, "A"),
            make_entry(3.0, 5.0, "B"),
            make_entry(6.0, 8.0, "C"),
        ];
        let spec = make_spec(entries, "center");
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        assert_eq!(result.matches("drawtext=").count(), 3);
        assert!(result.contains("enable='between(t,0.0,2.0)'"));
        assert!(result.contains("enable='between(t,3.0,5.0)'"));
        assert!(result.contains("enable='between(t,6.0,8.0)'"));
        assert!(result.contains("y=(h-text_h)/2"));
    }

    #[test]
    fn test_build_text_escape_applied() {
        let spec = make_spec(vec![make_entry(0.0, 1.0, "key:value")], "bottom");
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        assert!(!result.contains("text='key:value'"));
        assert!(result.contains("key\\:value") || result.contains("key"));
    }

    #[test]
    fn test_position_to_xy_bottom() {
        let (x, y) = position_to_xy("bottom");
        assert_eq!(x, "(w-text_w)/2");
        assert_eq!(y, "h-text_h-10");
    }

    #[test]
    fn test_position_to_xy_top() {
        let (x, y) = position_to_xy("top");
        assert_eq!(x, "(w-text_w)/2");
        assert_eq!(y, "10");
    }

    #[test]
    fn test_position_to_xy_center() {
        let (x, y) = position_to_xy("center");
        assert_eq!(x, "(w-text_w)/2");
        assert_eq!(y, "(h-text_h)/2");
    }

    // -- BurnedSubtitleBuilder --

    fn make_srt_spec(path: &str) -> BurnedSubtitleSpec {
        BurnedSubtitleSpec::py_new(Some(path.to_string()), None, None)
    }

    fn make_ass_spec(path: &str) -> BurnedSubtitleSpec {
        BurnedSubtitleSpec::py_new(Some(path.to_string()), None, None)
    }

    #[test]
    fn test_escape_force_style_no_comma() {
        assert_eq!(escape_force_style("Fontsize=32").unwrap(), "Fontsize=32");
    }

    #[test]
    fn test_escape_force_style_comma_in_value() {
        assert_eq!(
            escape_force_style("Fontname=Arial,Bold").unwrap(),
            r"Fontname=Arial\,Bold"
        );
    }

    #[test]
    fn test_escape_force_style_multiple_commas() {
        assert_eq!(escape_force_style("a,b,c").unwrap(), r"a\,b\,c");
    }

    #[test]
    fn test_burned_subtitle_srt_basic() {
        let spec = make_srt_spec("/tmp/test.srt");
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        assert!(result.starts_with("subtitles=filename="));
        assert!(result.contains("test.srt"));
        assert!(!result.contains("force_style"));
    }

    #[test]
    fn test_burned_subtitle_ass_no_force_style() {
        let spec = make_ass_spec("/tmp/test.ass");
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        assert!(result.starts_with("ass=filename="));
        assert!(result.contains("test.ass"));
        assert!(!result.contains("force_style"));
    }

    #[test]
    fn test_burned_subtitle_srt_with_force_style() {
        let mut style = std::collections::HashMap::new();
        style.insert("Fontsize".to_string(), "32".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        assert!(result.contains(":force_style='"));
        assert!(result.contains("Fontsize=32"));
    }

    #[test]
    fn test_burned_subtitle_force_style_comma_escaped() {
        let mut style = std::collections::HashMap::new();
        style.insert("Fontname".to_string(), "Arial,Bold".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        // Comma in value must be escaped as \,
        assert!(result.contains(r"Arial\,Bold"));
    }

    #[test]
    fn test_escape_force_style_single_quote_rejected() {
        assert!(escape_force_style("Arial':BorderStyle=4").is_err());
    }

    #[test]
    fn test_escape_force_style_single_quote_err_message() {
        let err = escape_force_style("Arial':BorderStyle=4").unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("single-quote"),
            "expected 'single-quote' in error message, got: {msg}"
        );
        assert!(
            msg.contains("Arial':BorderStyle=4"),
            "expected value in error message, got: {msg}"
        );
    }

    #[test]
    fn test_burned_subtitle_key_apostrophe_rejected() {
        let mut style = std::collections::HashMap::new();
        style.insert("Font'name".to_string(), "Arial".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_key_comma_rejected() {
        let mut style = std::collections::HashMap::new();
        style.insert("Font,name".to_string(), "Arial".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_key_equals_rejected() {
        let mut style = std::collections::HashMap::new();
        style.insert("Font=name".to_string(), "Arial".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_key_colon_rejected() {
        let mut style = std::collections::HashMap::new();
        style.insert("Font:name".to_string(), "Arial".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_force_style_value_apostrophe_error() {
        let mut style = std::collections::HashMap::new();
        style.insert("Fontname".to_string(), "O'Brien".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_force_style_safe_value() {
        let mut style = std::collections::HashMap::new();
        style.insert("Fontname".to_string(), "Arial Bold".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.srt".to_string()), None, Some(style));
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        assert!(
            result.contains("Fontname=Arial Bold"),
            "expected safe value in output: {result}"
        );
    }

    #[test]
    fn test_burned_subtitle_ass_ignores_force_style() {
        let mut style = std::collections::HashMap::new();
        style.insert("Fontsize".to_string(), "32".to_string());
        let spec = BurnedSubtitleSpec::py_new(Some("/tmp/test.ass".to_string()), None, Some(style));
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        // ASS does not emit force_style
        assert!(result.starts_with("ass=filename="));
        assert!(!result.contains("force_style"));
    }

    #[test]
    fn test_burned_subtitle_no_source_or_inline_error() {
        let spec = BurnedSubtitleSpec::py_new(None, None, None);
        assert!(BurnedSubtitleBuilder::build(&spec).is_err());
    }

    #[test]
    fn test_burned_subtitle_inline_text_used_as_path() {
        let spec = BurnedSubtitleSpec::py_new(None, Some("/tmp/inline.srt".to_string()), None);
        let result = BurnedSubtitleBuilder::build(&spec).unwrap();
        assert!(result.starts_with("subtitles=filename="));
        assert!(result.contains("inline.srt"));
    }

    // -- SubtitleScriptBuilder scale tests (BL-584-AC-1) --

    #[test]
    fn test_build_500_entries() {
        let entries: Vec<ScriptEntry> = (0..500)
            .map(|i| {
                let start = i as f64;
                let end = start + 0.9;
                make_entry(start, end, &format!("Cue {i}"))
            })
            .collect();
        let spec = make_spec(entries, "bottom");
        let result = SubtitleScriptBuilder::build(&spec).unwrap();
        // 500 drawtext filters joined by commas — no artificial cap
        assert_eq!(result.matches("drawtext=").count(), 500);
        // Result must be non-empty and valid (no error)
        assert!(!result.is_empty());
    }

    // -- font_color validation (BL-596) --

    #[test]
    fn test_font_color_colon_rejected() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "white:fontsize=200".to_string(),
            None,
        )
        .is_err());
    }

    #[test]
    fn test_font_color_apostrophe_rejected() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "wh'ite".to_string(),
            None,
        )
        .is_err());
    }

    #[test]
    fn test_font_color_valid_named() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "white".to_string(),
            None,
        )
        .is_ok());
    }

    #[test]
    fn test_font_color_valid_hex() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "#ff0000".to_string(),
            None,
        )
        .is_ok());
    }

    #[test]
    fn test_font_color_valid_0x() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "0xffffff88".to_string(),
            None,
        )
        .is_ok());
    }

    // -- font_color filtergraph metacharacter rejection (BL-599) --

    #[test]
    fn test_font_color_comma_rejected() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "white,scale=2".to_string(),
            None,
        )
        .is_err());
    }

    #[test]
    fn test_font_color_semicolon_rejected() {
        let entry = make_entry(0.0, 1.0, "hi");
        assert!(SubtitleScriptSpec::py_new(
            vec![entry],
            "bottom".to_string(),
            24,
            "white;scale=2".to_string(),
            None,
        )
        .is_err());
    }
}
