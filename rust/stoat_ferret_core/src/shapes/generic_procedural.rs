// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! GenericProceduralImageBuilder: per-pixel expression evaluator with PNG output.

use super::procedural_parser::{eval, parse, Expr, ParseError};
use image::{ImageBuffer, Luma, Rgba};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, PartialEq)]
enum OutputFormat {
    Rgba,
    Grayscale,
}

/// Procedural image builder using a bespoke recursive-descent expression parser.
///
/// Evaluates a user-supplied expression per pixel and saves RGBA or grayscale PNG output.
/// The expression is parsed at construction for fail-fast error reporting.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct GenericProceduralImageBuilder {
    expression: String,
    parsed: Expr,
    width: u32,
    height: u32,
    output_format: OutputFormat,
    at_time: f64,
}

#[pymethods]
impl GenericProceduralImageBuilder {
    #[new]
    #[pyo3(signature = (expression, width, height, output_format=None, at_time=None))]
    pub fn py_new(
        expression: &str,
        width: u32,
        height: u32,
        output_format: Option<&str>,
        at_time: Option<f64>,
    ) -> PyResult<Self> {
        if width == 0 || height == 0 {
            return Err(PyValueError::new_err("width and height must be > 0"));
        }
        let fmt = match output_format {
            None | Some("rgba") => OutputFormat::Rgba,
            Some("grayscale") => OutputFormat::Grayscale,
            Some(s) => {
                return Err(PyValueError::new_err(format!(
                    "output_format must be 'rgba' or 'grayscale', got '{s}'"
                )));
            }
        };
        let parsed = parse(expression).map_err(|e: ParseError| match e {
            ParseError::WrongArity {
                fn_name,
                expected_arity,
                got_arity,
            } => PyValueError::new_err(format!(
                "function '{fn_name}' expects {expected_arity} argument(s), got {got_arity}"
            )),
            _ => PyValueError::new_err(format!("expression parse error: {e}")),
        })?;
        Ok(Self {
            expression: expression.to_string(),
            parsed,
            width,
            height,
            output_format: fmt,
            at_time: at_time.unwrap_or(0.0),
        })
    }

    /// Render and save the procedural image to a PNG file.
    ///
    /// Args:
    ///     output_path: Destination file path (parent directories are created).
    ///
    /// Raises:
    ///     ValueError: If render times out, eval budget exceeded, or file cannot be written.
    #[pyo3(name = "synthesise")]
    pub fn py_synthesise(&self, output_path: &str) -> PyResult<()> {
        let path = std::path::Path::new(output_path);
        std::fs::create_dir_all(path.parent().unwrap_or(std::path::Path::new(".")))
            .map_err(|e| PyValueError::new_err(format!("cannot create output dir: {e}")))?;

        let w = self.width;
        let h = self.height;
        let t = self.at_time;
        let w_norm = (w.saturating_sub(1)).max(1) as f64;
        let h_norm = (h.saturating_sub(1)).max(1) as f64;

        // Per-render timeout: 5s base scaled by resolution vs 720p, clamped [5s, 60s]
        let pixel_count = w as u64 * h as u64;
        let base_pixels: u64 = 1280 * 720;
        let timeout_ms = (5000u64 * pixel_count / base_pixels).clamp(5000, 60000);
        let timeout = Duration::from_millis(timeout_ms);
        let start = Instant::now();

        match self.output_format {
            OutputFormat::Rgba => {
                let mut img: ImageBuffer<Rgba<u8>, Vec<u8>> = ImageBuffer::new(w, h);
                for py in 0..h {
                    // Per-row timeout check
                    if start.elapsed() > timeout {
                        return Err(PyValueError::new_err(format!(
                            "render timeout after {}ms",
                            timeout_ms
                        )));
                    }
                    let y = py as f64 / h_norm;
                    for px in 0..w {
                        let x = px as f64 / w_norm;
                        let mut budget = 10_000usize;
                        let v = eval(&self.parsed, x, y, t, &mut budget).map_err(|e| {
                            PyValueError::new_err(format!("eval error at ({px},{py}): {e}"))
                        })?;
                        let byte = (v.clamp(0.0, 1.0) * 255.0).round() as u8;
                        img.put_pixel(px, py, Rgba([byte, byte, byte, 255]));
                    }
                }
                img.save(path)
                    .map_err(|e| PyValueError::new_err(format!("cannot write PNG: {e}")))?;
            }
            OutputFormat::Grayscale => {
                let mut img: ImageBuffer<Luma<u8>, Vec<u8>> = ImageBuffer::new(w, h);
                for py in 0..h {
                    if start.elapsed() > timeout {
                        return Err(PyValueError::new_err(format!(
                            "render timeout after {}ms",
                            timeout_ms
                        )));
                    }
                    let y = py as f64 / h_norm;
                    for px in 0..w {
                        let x = px as f64 / w_norm;
                        let mut budget = 10_000usize;
                        let v = eval(&self.parsed, x, y, t, &mut budget).map_err(|e| {
                            PyValueError::new_err(format!("eval error at ({px},{py}): {e}"))
                        })?;
                        let byte = (v.clamp(0.0, 1.0) * 255.0).round() as u8;
                        img.put_pixel(px, py, Luma([byte]));
                    }
                }
                img.save(path)
                    .map_err(|e| PyValueError::new_err(format!("cannot write PNG: {e}")))?;
            }
        }

        Ok(())
    }

    fn __repr__(&self) -> String {
        format!(
            "GenericProceduralImageBuilder(expression={:?}, width={}, height={}, output_format={:?}, at_time={})",
            self.expression,
            self.width,
            self.height,
            match self.output_format {
                OutputFormat::Rgba => "rgba",
                OutputFormat::Grayscale => "grayscale",
            },
            self.at_time,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp_path(name: &str) -> std::path::PathBuf {
        std::env::temp_dir()
            .join("snf_generic_procedural")
            .join(name)
    }

    fn ensure_dir(p: &std::path::Path) {
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    }

    #[test]
    fn test_build_budget_256x256() {
        let builder =
            GenericProceduralImageBuilder::py_new("sin(x*6.28)*cos(y*6.28)", 256, 256, None, None)
                .unwrap();
        let out = tmp_path("budget_test.png");
        ensure_dir(&out);
        let start = std::time::Instant::now();
        builder.py_synthesise(out.to_str().unwrap()).unwrap();
        let elapsed = start.elapsed().as_millis();
        assert!(elapsed < 2000, "render exceeded 2000ms budget: {elapsed}ms");
    }

    #[test]
    fn test_render_determinism() {
        let builder = GenericProceduralImageBuilder::py_new(
            "sin(atan2(y-0.5,x-0.5)*4+t*6.28)*0.5+0.5",
            64,
            64,
            None,
            Some(0.5),
        )
        .unwrap();
        let out1 = tmp_path("det1.png");
        let out2 = tmp_path("det2.png");
        ensure_dir(&out1);
        builder.py_synthesise(out1.to_str().unwrap()).unwrap();
        builder.py_synthesise(out2.to_str().unwrap()).unwrap();
        let img1 = image::open(&out1).unwrap().to_rgba8();
        let img2 = image::open(&out2).unwrap().to_rgba8();
        assert_eq!(img1.as_raw(), img2.as_raw(), "render is not deterministic");
    }

    #[test]
    fn test_render_linear_gradient() {
        let builder = GenericProceduralImageBuilder::py_new("x", 64, 64, None, None).unwrap();
        let out = tmp_path("gradient.png");
        ensure_dir(&out);
        builder.py_synthesise(out.to_str().unwrap()).unwrap();
        let img = image::open(&out).unwrap().to_rgba8();
        // First pixel (x=0) should have R ≈ 0; last pixel in first row (x=63/63=1.0) should be ≈ 255
        let first = img.get_pixel(0, 0)[0];
        let last = img.get_pixel(63, 0)[0];
        assert!(first < 5, "first pixel R={first}, expected ~0");
        assert!(last > 250, "last pixel R={last}, expected ~255");
    }

    #[test]
    fn test_render_radial() {
        let builder =
            GenericProceduralImageBuilder::py_new("hypot(x-0.5, y-0.5)", 64, 64, None, None)
                .unwrap();
        let out = tmp_path("radial.png");
        ensure_dir(&out);
        builder.py_synthesise(out.to_str().unwrap()).unwrap();
        let img = image::open(&out).unwrap().to_rgba8();
        let center = img.get_pixel(32, 32)[0];
        let corner = img.get_pixel(0, 0)[0];
        assert!(
            center < corner,
            "center ({center}) should be darker than corner ({corner})"
        );
    }

    #[test]
    fn test_invalid_expression_error() {
        let r = GenericProceduralImageBuilder::py_new("foo_bar", 64, 64, None, None);
        assert!(r.is_err(), "unknown ident should error at construction");
    }

    #[test]
    fn test_zero_dimension_error() {
        assert!(GenericProceduralImageBuilder::py_new("x", 0, 64, None, None).is_err());
        assert!(GenericProceduralImageBuilder::py_new("x", 64, 0, None, None).is_err());
    }

    #[test]
    fn test_invalid_output_format_error() {
        let r = GenericProceduralImageBuilder::py_new("x", 64, 64, Some("invalid_format"), None);
        assert!(r.is_err());
    }

    #[test]
    fn test_grayscale_output() {
        let builder =
            GenericProceduralImageBuilder::py_new("x", 64, 64, Some("grayscale"), None).unwrap();
        let out = tmp_path("gray.png");
        ensure_dir(&out);
        builder.py_synthesise(out.to_str().unwrap()).unwrap();
        let img = image::open(&out).unwrap().to_luma8();
        let first = img.get_pixel(0, 0)[0];
        let last = img.get_pixel(63, 0)[0];
        assert!(first < 5, "first gray pixel={first}, expected ~0");
        assert!(last > 250, "last gray pixel={last}, expected ~255");
    }
}
