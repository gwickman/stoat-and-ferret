//! Overlay and scale filter builders for composition layouts.
//!
//! Converts [`LayoutPosition`] normalized coordinates into FFmpeg `overlay` and
//! `scale` filter strings for multi-stream composition (e.g., PIP, split-screen).
//!
//! The overlay filter positions one video stream over another but does **not**
//! scale inputs, so a separate `scale` filter must be applied first.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyfunction;

use crate::layout::position::LayoutPosition;

/// Rounds a value to the nearest even number (minimum 2).
///
/// FFmpeg requires even dimensions when using certain codecs (e.g., H.264).
fn round_even(value: f64) -> u32 {
    let rounded = value.round() as i64;
    let even = if rounded % 2 == 0 {
        rounded
    } else {
        rounded + 1
    };
    even.max(2) as u32
}

/// Builds an FFmpeg overlay filter string from a layout position.
///
/// Converts the position's normalized `x` and `y` coordinates to pixel values
/// and generates an overlay filter with a time-based enable expression.
///
/// # Arguments
///
/// * `position` - Layout position with normalized coordinates
/// * `output_w` - Output canvas width in pixels
/// * `output_h` - Output canvas height in pixels
/// * `start` - Start time in seconds for the overlay enable window
/// * `end` - End time in seconds for the overlay enable window
///
/// # Returns
///
/// A string like `overlay=x=480:y=540:enable='between(t,0,5)'`
#[must_use]
pub fn build_overlay_filter(
    position: &LayoutPosition,
    output_w: u32,
    output_h: u32,
    start: f64,
    end: f64,
) -> String {
    let (px, py, _, _) = position.to_pixels(output_w, output_h);
    format!(
        "overlay=x={px}:y={py}:enable='between(t,{start},{end})'",
        px = px,
        py = py,
        start = start,
        end = end,
    )
}

/// Builds an FFmpeg scale filter string from a layout position.
///
/// Converts the position's normalized `width` and `height` to pixel dimensions,
/// ensuring they are even numbers (required by many codecs). Optionally preserves
/// the original aspect ratio.
///
/// # Arguments
///
/// * `position` - Layout position with normalized coordinates
/// * `output_w` - Output canvas width in pixels
/// * `output_h` - Output canvas height in pixels
/// * `preserve_aspect` - When `true`, adds `force_original_aspect_ratio=decrease`
///
/// # Returns
///
/// A string like `scale=w=960:h=540:force_divisible_by=2` or with
/// `:force_original_aspect_ratio=decrease` appended when preserving aspect ratio.
#[must_use]
pub fn build_scale_for_layout(
    position: &LayoutPosition,
    output_w: u32,
    output_h: u32,
    preserve_aspect: bool,
) -> String {
    let w_f = f64::from(output_w);
    let h_f = f64::from(output_h);

    let (_, _, raw_w, raw_h) = position.to_pixels(output_w, output_h);

    let target_w = round_even(raw_w as f64 * w_f / w_f);
    let target_h = round_even(raw_h as f64 * h_f / h_f);

    if preserve_aspect {
        format!(
            "scale=w={target_w}:h={target_h}:force_divisible_by=2:force_original_aspect_ratio=decrease",
        )
    } else {
        format!("scale=w={target_w}:h={target_h}:force_divisible_by=2",)
    }
}

// ---------------------------------------------------------------------------
// PyO3 bindings
// ---------------------------------------------------------------------------

/// Builds an FFmpeg overlay filter string from a LayoutPosition.
///
/// Converts normalized coordinates to pixel positions and generates an
/// overlay filter with time-based enable expression.
///
/// Args:
///     position: Layout position with normalized coordinates (0.0-1.0).
///     output_w: Output canvas width in pixels.
///     output_h: Output canvas height in pixels.
///     start: Start time in seconds for the overlay.
///     end: End time in seconds for the overlay.
///
/// Returns:
///     FFmpeg overlay filter string.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "build_overlay_filter")]
fn py_build_overlay_filter(
    position: &LayoutPosition,
    output_w: u32,
    output_h: u32,
    start: f64,
    end: f64,
) -> String {
    build_overlay_filter(position, output_w, output_h, start, end)
}

/// Builds an FFmpeg scale filter string from a LayoutPosition.
///
/// Converts normalized dimensions to pixel values with even-number
/// enforcement and optional aspect ratio preservation.
///
/// Args:
///     position: Layout position with normalized coordinates (0.0-1.0).
///     output_w: Output canvas width in pixels.
///     output_h: Output canvas height in pixels.
///     preserve_aspect: If true, preserves original aspect ratio.
///
/// Returns:
///     FFmpeg scale filter string.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "build_scale_for_layout")]
fn py_build_scale_for_layout(
    position: &LayoutPosition,
    output_w: u32,
    output_h: u32,
    preserve_aspect: bool,
) -> String {
    build_scale_for_layout(position, output_w, output_h, preserve_aspect)
}

/// Registers compose overlay functions with the Python module.
pub fn register(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_build_overlay_filter, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_scale_for_layout, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- build_overlay_filter tests --

    #[test]
    fn overlay_pip_bottom_right() {
        // PIP at bottom-right quarter: x=0.5, y=0.5
        let pos = LayoutPosition::new(0.5, 0.5, 0.25, 0.25, 1);
        let result = build_overlay_filter(&pos, 1920, 1080, 0.0, 5.0);
        assert_eq!(
            result,
            "overlay=x=960:y=540:enable='between(t,0,5)'"
        );
    }

    #[test]
    fn overlay_full_screen() {
        let pos = LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0);
        let result = build_overlay_filter(&pos, 1920, 1080, 1.5, 10.0);
        assert_eq!(
            result,
            "overlay=x=0:y=0:enable='between(t,1.5,10)'"
        );
    }

    #[test]
    fn overlay_center_position() {
        // Center of a 1280x720 canvas
        let pos = LayoutPosition::new(0.25, 0.25, 0.5, 0.5, 0);
        let result = build_overlay_filter(&pos, 1280, 720, 0.0, 3.0);
        assert_eq!(
            result,
            "overlay=x=320:y=180:enable='between(t,0,3)'"
        );
    }

    #[test]
    fn overlay_4k_resolution() {
        let pos = LayoutPosition::new(0.75, 0.75, 0.25, 0.25, 0);
        let result = build_overlay_filter(&pos, 3840, 2160, 2.0, 8.0);
        assert_eq!(
            result,
            "overlay=x=2880:y=1620:enable='between(t,2,8)'"
        );
    }

    // -- build_scale_for_layout tests --

    #[test]
    fn scale_half_screen_no_aspect() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0);
        let result = build_scale_for_layout(&pos, 1920, 1080, false);
        assert_eq!(result, "scale=w=960:h=540:force_divisible_by=2");
    }

    #[test]
    fn scale_half_screen_preserve_aspect() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0);
        let result = build_scale_for_layout(&pos, 1920, 1080, true);
        assert_eq!(
            result,
            "scale=w=960:h=540:force_divisible_by=2:force_original_aspect_ratio=decrease"
        );
    }

    #[test]
    fn scale_full_screen() {
        let pos = LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0);
        let result = build_scale_for_layout(&pos, 1920, 1080, false);
        assert_eq!(result, "scale=w=1920:h=1080:force_divisible_by=2");
    }

    #[test]
    fn scale_quarter_screen_720p() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.25, 0.25, 0);
        let result = build_scale_for_layout(&pos, 1280, 720, false);
        assert_eq!(result, "scale=w=320:h=180:force_divisible_by=2");
    }

    #[test]
    fn scale_produces_even_dimensions() {
        // 0.33 * 1920 = 633.6 -> rounds to 634 (even)
        let pos = LayoutPosition::new(0.0, 0.0, 0.33, 0.33, 0);
        let result = build_scale_for_layout(&pos, 1920, 1080, false);
        // Extract w and h from the filter string
        let w_part = result.split("w=").nth(1).unwrap().split(':').next().unwrap();
        let h_part = result.split("h=").nth(1).unwrap().split(':').next().unwrap();
        let w: u32 = w_part.parse().unwrap();
        let h: u32 = h_part.parse().unwrap();
        assert_eq!(w % 2, 0, "Width {w} must be even");
        assert_eq!(h % 2, 0, "Height {h} must be even");
    }

    #[test]
    fn scale_4k_pip() {
        let pos = LayoutPosition::new(0.75, 0.75, 0.25, 0.25, 0);
        let result = build_scale_for_layout(&pos, 3840, 2160, true);
        assert_eq!(
            result,
            "scale=w=960:h=540:force_divisible_by=2:force_original_aspect_ratio=decrease"
        );
    }

    // -- round_even tests --

    #[test]
    fn round_even_already_even() {
        assert_eq!(round_even(100.0), 100);
    }

    #[test]
    fn round_even_rounds_up_odd() {
        assert_eq!(round_even(101.0), 102);
    }

    #[test]
    fn round_even_fractional() {
        assert_eq!(round_even(99.5), 100);
    }

    #[test]
    fn round_even_minimum() {
        assert_eq!(round_even(0.0), 2);
        assert_eq!(round_even(1.0), 2);
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn overlay_contains_required_parts(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.0f64..=1.0,
            h in 0.0f64..=1.0,
            z in -100i32..=100,
            out_w in 2u32..=7680,
            out_h in 2u32..=7680,
            start in 0.0f64..=100.0,
            end in 0.0f64..=100.0,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            let result = build_overlay_filter(&pos, out_w, out_h, start, end);
            prop_assert!(result.starts_with("overlay="), "Must start with overlay=: {}", result);
            prop_assert!(result.contains("x="), "Must contain x=: {}", result);
            prop_assert!(result.contains("y="), "Must contain y=: {}", result);
            prop_assert!(result.contains("enable="), "Must contain enable=: {}", result);
            prop_assert!(result.contains("between(t,"), "Must contain between(t,: {}", result);
        }

        #[test]
        fn overlay_pixel_values_non_negative(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.0f64..=1.0,
            h in 0.0f64..=1.0,
            z in -100i32..=100,
            out_w in 2u32..=7680,
            out_h in 2u32..=7680,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            let (px, py, _, _) = pos.to_pixels(out_w, out_h);
            // Pixel values from valid normalized coords must be non-negative
            prop_assert!(px >= 0, "x pixel value must be non-negative: {}", px);
            prop_assert!(py >= 0, "y pixel value must be non-negative: {}", py);
            // The overlay filter must embed these values
            let result = build_overlay_filter(&pos, out_w, out_h, 0.0, 1.0);
            prop_assert!(
                result.contains(&format!("x={px}")),
                "overlay must contain x={px}: {result}"
            );
            prop_assert!(
                result.contains(&format!("y={py}")),
                "overlay must contain y={py}: {result}"
            );
        }

        #[test]
        fn scale_contains_required_parts(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.01f64..=1.0,
            h in 0.01f64..=1.0,
            z in -100i32..=100,
            out_w in 2u32..=7680,
            out_h in 2u32..=7680,
            preserve in proptest::bool::ANY,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            let result = build_scale_for_layout(&pos, out_w, out_h, preserve);
            prop_assert!(result.starts_with("scale="), "Must start with scale=: {}", result);
            prop_assert!(result.contains("w="), "Must contain w=: {}", result);
            prop_assert!(result.contains("h="), "Must contain h=: {}", result);
            prop_assert!(result.contains("force_divisible_by=2"), "Must contain force_divisible_by=2: {}", result);
            if preserve {
                prop_assert!(
                    result.contains("force_original_aspect_ratio=decrease"),
                    "Must contain force_original_aspect_ratio=decrease when preserve_aspect=true: {}", result
                );
            }
        }

        #[test]
        fn scale_dimensions_are_positive_even(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.01f64..=1.0,
            h in 0.01f64..=1.0,
            z in -100i32..=100,
            out_w in 2u32..=7680,
            out_h in 2u32..=7680,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            let result = build_scale_for_layout(&pos, out_w, out_h, false);
            // Extract w value
            let w_val: u32 = result
                .split("w=").nth(1).unwrap()
                .split(':').next().unwrap()
                .parse().unwrap();
            // Extract h value
            let h_val: u32 = result
                .split("h=").nth(1).unwrap()
                .split(':').next().unwrap()
                .parse().unwrap();
            prop_assert!(w_val > 0, "Width must be positive: {}", w_val);
            prop_assert!(h_val > 0, "Height must be positive: {}", h_val);
            prop_assert!(w_val % 2 == 0, "Width must be even: {}", w_val);
            prop_assert!(h_val % 2 == 0, "Height must be even: {}", h_val);
        }
    }
}
