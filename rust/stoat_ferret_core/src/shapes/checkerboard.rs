// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Checkerboard procedural generator.

use image::{ImageBuffer, Rgba};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Procedural checkerboard pattern generator. Outputs RGBA PNG.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct CheckerboardGenerator {
    square_size: u32,
}

#[pymethods]
impl CheckerboardGenerator {
    #[new]
    pub fn py_new(square_size: u32) -> PyResult<Self> {
        if square_size == 0 {
            return Err(PyValueError::new_err("square_size must be > 0"));
        }
        Ok(Self { square_size })
    }

    /// Render the checkerboard to an RGBA PNG at the given path.
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

impl CheckerboardGenerator {
    pub(crate) fn generate(&self, width: u32, height: u32) -> ImageBuffer<Rgba<u8>, Vec<u8>> {
        let sq = self.square_size;
        ImageBuffer::from_fn(width, height, |x, y| {
            // Integer-only logic — guaranteed bit-identical across all platforms
            let checker = ((x / sq) + (y / sq)) % 2;
            if checker == 0 {
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
    fn test_checkerboard_generation_budget() {
        let gen = CheckerboardGenerator::py_new(32).unwrap();
        let start = std::time::Instant::now();
        let _ = gen.generate(1080, 1080);
        let elapsed = start.elapsed().as_millis();
        assert!(elapsed < 100, "generation exceeded 100ms budget: {elapsed}ms");
    }

    #[test]
    fn test_checkerboard_pixel_hash() {
        // Pure integer math → guaranteed bit-identical across all platforms.
        // Pinned on 2026-06-27. Defends against accidental math regressions.
        const PINNED: &str = "da3b1f98601232db4e7b5c211cc7614dd9125f1f3db81b2f6beb612accda8c12";
        let gen = CheckerboardGenerator::py_new(8).unwrap();
        let img = gen.generate(64, 64);
        let hash = hash_raw(&img);
        assert_eq!(hash, PINNED, "checkerboard pixel buffer hash mismatch — math regression?");
        // With 8x8 squares and 64x64 image: exactly half the pixels are white
        let white_count = img.pixels().filter(|&&p| p == Rgba([255, 255, 255, 255])).count();
        assert_eq!(white_count, 64 * 64 / 2, "checker must be exactly half white");
    }

    #[test]
    fn test_checkerboard_invalid_params() {
        assert!(CheckerboardGenerator::py_new(0).is_err());
    }

    #[test]
    fn test_checkerboard_single_pixel_pattern() {
        // 1x1 squares: alternating per-pixel
        let gen = CheckerboardGenerator::py_new(1).unwrap();
        let img = gen.generate(4, 4);
        // (0,0): (0/1 + 0/1) % 2 = 0 → white
        assert_eq!(img.get_pixel(0, 0), &Rgba([255, 255, 255, 255]));
        // (1,0): (1/1 + 0/1) % 2 = 1 → black
        assert_eq!(img.get_pixel(1, 0), &Rgba([0, 0, 0, 255]));
        // (0,1): (0/1 + 1/1) % 2 = 1 → black
        assert_eq!(img.get_pixel(0, 1), &Rgba([0, 0, 0, 255]));
        // (1,1): (1/1 + 1/1) % 2 = 0 → white
        assert_eq!(img.get_pixel(1, 1), &Rgba([255, 255, 255, 255]));
    }
}
