// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Concentric rings procedural generator.

use image::{ImageBuffer, Rgba};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Procedural concentric rings pattern generator. Outputs RGBA PNG.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ConcentricRingsGenerator {
    ring_count: u32,
    ring_width: f32,
}

#[pymethods]
impl ConcentricRingsGenerator {
    #[new]
    pub fn py_new(ring_count: u32, ring_width: f32) -> PyResult<Self> {
        if ring_count == 0 {
            return Err(PyValueError::new_err("ring_count must be > 0"));
        }
        if ring_width <= 0.0 || ring_width >= 1.0 {
            return Err(PyValueError::new_err("ring_width must be in (0, 1)"));
        }
        Ok(Self {
            ring_count,
            ring_width,
        })
    }

    /// Render the concentric rings to an RGBA PNG at the given path.
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

impl ConcentricRingsGenerator {
    pub(crate) fn generate(&self, width: u32, height: u32) -> ImageBuffer<Rgba<u8>, Vec<u8>> {
        let cx = width as f32 / 2.0;
        let cy = height as f32 / 2.0;
        let max_r = cx.min(cy);

        ImageBuffer::from_fn(width, height, |x, y| {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let r = (dx * dx + dy * dy).sqrt();
            if r > max_r {
                return Rgba([0, 0, 0, 255]);
            }
            let r_norm = r / max_r;
            // Fraction within current ring band
            let ring_phase = (r_norm * self.ring_count as f32).fract();
            if ring_phase < self.ring_width {
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
    fn test_concentric_rings_generation_budget() {
        let gen = ConcentricRingsGenerator::py_new(8, 0.4).unwrap();
        let start = std::time::Instant::now();
        let _ = gen.generate(1080, 1080);
        let elapsed = start.elapsed().as_millis();
        assert!(
            elapsed < 100,
            "generation exceeded 100ms budget: {elapsed}ms"
        );
    }

    #[test]
    fn test_concentric_rings_pixel_hash() {
        // Pinned on 2026-06-27 (Windows x86_64). Defends against accidental math regressions.
        const PINNED: &str = "17015cc3813279ca80d573df146b8667a6536281638d838cc2446e491499a90d";
        let gen = ConcentricRingsGenerator::py_new(8, 0.4).unwrap();
        let img = gen.generate(64, 64);
        let hash = hash_raw(&img);
        assert_eq!(
            hash, PINNED,
            "concentric rings pixel buffer hash mismatch — math regression?"
        );
    }

    #[test]
    fn test_concentric_rings_invalid_params() {
        assert!(ConcentricRingsGenerator::py_new(0, 0.4).is_err());
        assert!(ConcentricRingsGenerator::py_new(8, 0.0).is_err());
        assert!(ConcentricRingsGenerator::py_new(8, 1.0).is_err());
        assert!(ConcentricRingsGenerator::py_new(8, -0.1).is_err());
    }
}
