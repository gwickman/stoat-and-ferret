// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Archimedean spiral procedural generator.

use image::{ImageBuffer, Rgba};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::f32::consts::PI;

/// Procedural Archimedean spiral pattern generator. Outputs RGBA PNG.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SpiralGenerator {
    turn_count: f32,
    thickness: f32,
}

#[pymethods]
impl SpiralGenerator {
    #[new]
    pub fn py_new(turn_count: f32, thickness: f32) -> PyResult<Self> {
        if turn_count <= 0.0 {
            return Err(PyValueError::new_err("turn_count must be > 0"));
        }
        if thickness <= 0.0 {
            return Err(PyValueError::new_err("thickness must be > 0"));
        }
        Ok(Self {
            turn_count,
            thickness,
        })
    }

    /// Render the spiral to an RGBA PNG at the given path.
    ///
    /// AC-4 placeholder: parent directory is std::env::temp_dir()/snf_shapes.
    /// Stable snf-managed asset path integration is deferred to BL-511 (v090).
    #[pyo3(name = "render_to_file")]
    pub fn py_render_to_file(&self, output_path: &str, width: u32, height: u32) -> PyResult<()> {
        if width == 0 || height == 0 {
            return Err(PyValueError::new_err("width and height must be > 0"));
        }
        let img = self.generate(width, height);
        let path = std::path::Path::new(output_path);
        std::fs::create_dir_all(path.parent().unwrap_or(std::path::Path::new(".")))
            .map_err(|e| PyValueError::new_err(format!("Cannot create output dir: {e}")))?;
        img.save(path)
            .map_err(|e| PyValueError::new_err(format!("Cannot write PNG: {e}")))?;
        Ok(())
    }
}

impl SpiralGenerator {
    pub(crate) fn generate(&self, width: u32, height: u32) -> ImageBuffer<Rgba<u8>, Vec<u8>> {
        let cx = width as f32 / 2.0;
        let cy = height as f32 / 2.0;
        let max_r = cx.min(cy);
        // Normalise thickness to fraction of max_r, halved for one-sided band
        let norm_thickness = self.thickness / max_r / 2.0;

        ImageBuffer::from_fn(width, height, |x, y| {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let r = (dx * dx + dy * dy).sqrt();
            if r > max_r || r < 1e-6 {
                return Rgba([0, 0, 0, 255]);
            }
            let r_norm = r / max_r;
            // atan2(dy, dx) in [-PI, PI]; normalise to [0, 1]
            let theta_norm = (dy.atan2(dx) + PI) / (2.0 * PI);
            // Archimedean spiral phase: r_norm * turn_count advances by 1 per full outward turn
            let phase = (r_norm * self.turn_count - theta_norm).fract().abs();
            let min_phase = phase.min(1.0 - phase);
            if min_phase < norm_thickness {
                Rgba([255, 255, 255, 255])
            } else {
                Rgba([0, 0, 0, 255])
            }
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};

    fn hash_raw(img: &ImageBuffer<Rgba<u8>, Vec<u8>>) -> String {
        let mut h = Sha256::new();
        h.update(img.as_raw());
        format!("{:x}", h.finalize())
    }

    #[test]
    fn test_spiral_generation_budget() {
        let gen = SpiralGenerator::py_new(3.0, 2.0).unwrap();
        let start = std::time::Instant::now();
        let _ = gen.generate(256, 256);
        let elapsed = start.elapsed().as_millis();
        assert!(
            elapsed < 1000,
            "generation exceeded 1000ms budget: {elapsed}ms"
        );
    }

    #[test]
    fn test_spiral_pixel_hash() {
        // Pinned on 2026-06-27 (Windows x86_64). Defends against accidental math regressions.
        // On x86_64 (Windows/Linux/macOS), f32 IEEE 754 ops give bit-identical results.
        const PINNED: &str = "9f789efb7ae4d2b7aca55be8c79708914759ce02d5a9b12d70f1301c4c2c89c3";
        let gen = SpiralGenerator::py_new(3.0, 2.0).unwrap();
        let img = gen.generate(64, 64);
        let hash = hash_raw(&img);
        assert_eq!(
            hash, PINNED,
            "spiral pixel buffer hash mismatch — math regression?"
        );
    }

    #[test]
    fn test_spiral_zero_dimension_error() {
        let gen = SpiralGenerator::py_new(3.0, 2.0).unwrap();
        let tmp = std::env::temp_dir().join("snf_shapes/test_err.png");
        std::fs::create_dir_all(tmp.parent().unwrap()).unwrap();
        assert!(gen.py_render_to_file(tmp.to_str().unwrap(), 0, 64).is_err());
        assert!(gen.py_render_to_file(tmp.to_str().unwrap(), 64, 0).is_err());
    }

    #[test]
    fn test_spiral_invalid_params() {
        assert!(SpiralGenerator::py_new(0.0, 2.0).is_err());
        assert!(SpiralGenerator::py_new(-1.0, 2.0).is_err());
        assert!(SpiralGenerator::py_new(3.0, 0.0).is_err());
        assert!(SpiralGenerator::py_new(3.0, -1.0).is_err());
    }
}
