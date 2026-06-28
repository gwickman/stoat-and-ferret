// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Radial burst (sunburst) procedural generator.

use image::{ImageBuffer, Rgba};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::f32::consts::PI;

/// Procedural radial burst (sunburst) pattern generator. Outputs RGBA PNG.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct RadialBurstGenerator {
    ray_count: u32,
    ray_width: f32,
}

#[pymethods]
impl RadialBurstGenerator {
    #[new]
    pub fn py_new(ray_count: u32, ray_width: f32) -> PyResult<Self> {
        if ray_count == 0 {
            return Err(PyValueError::new_err("ray_count must be > 0"));
        }
        if !ray_width.is_finite() {
            return Err(PyValueError::new_err("ray_width must be finite"));
        }
        if ray_width <= 0.0 || ray_width >= 1.0 {
            return Err(PyValueError::new_err("ray_width must be in (0, 1)"));
        }
        Ok(Self {
            ray_count,
            ray_width,
        })
    }

    /// Render the radial burst to an RGBA PNG at the given path.
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

impl RadialBurstGenerator {
    pub(crate) fn generate(&self, width: u32, height: u32) -> ImageBuffer<Rgba<u8>, Vec<u8>> {
        let cx = width as f32 / 2.0;
        let cy = height as f32 / 2.0;
        let half = self.ray_width / 2.0;

        ImageBuffer::from_fn(width, height, |x, y| {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            if dx.abs() < 1e-6 && dy.abs() < 1e-6 {
                return Rgba([255, 255, 255, 255]);
            }
            // atan2(dy, dx) in [-PI, PI]; normalise to [0, 1]
            let theta_norm = (dy.atan2(dx) + PI) / (2.0 * PI);
            // fraction within current ray sector
            let ray_phase = (theta_norm * self.ray_count as f32).fract();
            if ray_phase < half || ray_phase > 1.0 - half {
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
    fn test_radial_burst_generation_budget() {
        let gen = RadialBurstGenerator::py_new(12, 0.4).unwrap();
        let start = std::time::Instant::now();
        let _ = gen.generate(256, 256);
        let elapsed = start.elapsed().as_millis();
        assert!(
            elapsed < 1000,
            "generation exceeded 1000ms budget: {elapsed}ms"
        );
    }

    #[test]
    fn test_radial_burst_pixel_hash() {
        // Pinned on 2026-06-27 (Windows x86_64). Defends against accidental math regressions.
        const PINNED: &str = "5d8498dda652f25128c72c1fa8e5490c3e570c10e7a3e389106ec768d461870c";
        let gen = RadialBurstGenerator::py_new(12, 0.4).unwrap();
        let img = gen.generate(64, 64);
        let hash = hash_raw(&img);
        assert_eq!(
            hash, PINNED,
            "radial burst pixel buffer hash mismatch — math regression?"
        );
    }

    #[test]
    fn test_radial_burst_invalid_params() {
        assert!(RadialBurstGenerator::py_new(0, 0.4).is_err());
        assert!(RadialBurstGenerator::py_new(12, 0.0).is_err());
        assert!(RadialBurstGenerator::py_new(12, 1.0).is_err());
        assert!(RadialBurstGenerator::py_new(12, -0.1).is_err());
    }
}
