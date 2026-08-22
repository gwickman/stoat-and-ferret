// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Crop filter builder.
//!
//! [`CropBuilder`] generates the FFmpeg `crop=w:h:x:y` filter string.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Pixel-coordinate crop filter builder.
///
/// `build()` emits `crop=w:h:x:y`.  Width and height must be > 0;
/// bounds clamping for out-of-range x/y is delegated to FFmpeg at runtime
/// (consistent with `ScaleBuilder`).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct CropBuilder {
    w: u32,
    h: u32,
    x: u32,
    y: u32,
}

#[pymethods]
impl CropBuilder {
    #[new]
    pub fn py_new(w: u32, h: u32, x: u32, y: u32) -> PyResult<Self> {
        if w == 0 || h == 0 {
            return Err(PyValueError::new_err("width and height must be > 0"));
        }
        Ok(Self { w, h, x, y })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> String {
        format!("crop={}:{}:{}:{}", self.w, self.h, self.x, self.y)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reject_zero_width() {
        assert!(CropBuilder::py_new(0, 100, 0, 0).is_err());
    }

    #[test]
    fn test_reject_zero_height() {
        assert!(CropBuilder::py_new(100, 0, 0, 0).is_err());
    }

    #[test]
    fn test_build_emits_correct_filter() {
        let b = CropBuilder::py_new(640, 360, 100, 50).unwrap();
        assert_eq!(b.py_build(), "crop=640:360:100:50");
    }

    #[test]
    fn test_build_zero_offset() {
        let b = CropBuilder::py_new(1280, 720, 0, 0).unwrap();
        assert_eq!(b.py_build(), "crop=1280:720:0:0");
    }
}
