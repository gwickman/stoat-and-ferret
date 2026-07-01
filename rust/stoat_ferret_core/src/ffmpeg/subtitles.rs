// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Subtitle effect builders for drawtext caption chains.
//!
//! Provides [`SubtitleScriptBuilder`] which emits N `drawtext` filters
//! chained with `enable='between(t,s,e)'` expressions for timed captions.

use pyo3::prelude::*;

use crate::ffmpeg::drawtext::escape_drawtext;

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
                Some(path) => format!("fontfile={}:", path),
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
        "bottom" => (
            "(w-text_w)/2".to_string(),
            "h-text_h-10".to_string(),
        ),
        "top" => (
            "(w-text_w)/2".to_string(),
            "10".to_string(),
        ),
        "center" => (
            "(w-text_w)/2".to_string(),
            "(h-text_h)/2".to_string(),
        ),
        // Unreachable: SubtitleScriptSpec::py_new rejects unknown positions.
        _ => (
            "(w-text_w)/2".to_string(),
            "h-text_h-10".to_string(),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
        let entry = ScriptEntry::py_new(0.0, 2.0, "hello".to_string()).unwrap();
        assert_eq!(entry.start_s, 0.0);
        assert_eq!(entry.end_s, 2.0);
        assert_eq!(entry.text, "hello");
    }

    #[test]
    fn test_subtitle_script_spec_rejects_unknown_position() {
        let entry = ScriptEntry::py_new(0.0, 1.0, "hi".to_string()).unwrap();
        assert!(
            SubtitleScriptSpec::py_new(vec![entry], "left".to_string(), 24, "white".to_string(), None)
                .is_err()
        );
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
}
