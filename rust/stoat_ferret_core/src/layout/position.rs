//! Layout position with normalized coordinates and pixel conversion.
//!
//! [`LayoutPosition`] uses normalized coordinates (0.0-1.0) for resolution-independent
//! positioning. Pixel conversion via [`LayoutPosition::to_pixels`] uses `round()` for
//! best-fit mapping; 1-pixel asymmetry at odd resolutions is expected behavior.

use std::fmt;

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Error type for layout validation failures.
#[derive(Debug, Clone, PartialEq)]
pub enum LayoutError {
    /// A coordinate field is outside the valid 0.0-1.0 range.
    OutOfRange {
        /// Name of the field that failed validation.
        field: String,
        /// The invalid value.
        value: f64,
    },
}

impl fmt::Display for LayoutError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LayoutError::OutOfRange { field, value } => {
                write!(f, "{field} must be in range 0.0-1.0, got {value}")
            }
        }
    }
}

impl std::error::Error for LayoutError {}

impl From<LayoutError> for PyErr {
    fn from(err: LayoutError) -> PyErr {
        crate::LayoutError::new_err(err.to_string())
    }
}

/// A layout position using normalized coordinates (0.0-1.0).
///
/// All coordinate fields (x, y, width, height) are normalized to the range
/// 0.0-1.0, representing fractions of the output dimensions. The `z_index`
/// field controls stacking order (higher values are drawn on top).
///
/// # Pixel Conversion
///
/// [`LayoutPosition::to_pixels`] converts normalized coordinates to integer
/// pixel values using `round()`. At odd output resolutions, this may produce
/// 1-pixel asymmetry — this is expected behavior.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::layout::position::LayoutPosition;
///
/// // Full-screen position
/// let pos = LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0);
/// assert_eq!(pos.to_pixels(1920, 1080), (0, 0, 1920, 1080));
///
/// // Quarter-screen top-left
/// let pos = LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0);
/// assert_eq!(pos.to_pixels(1920, 1080), (0, 0, 960, 540));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct LayoutPosition {
    x: f64,
    y: f64,
    width: f64,
    height: f64,
    z_index: i32,
}

impl LayoutPosition {
    /// Creates a new layout position.
    #[must_use]
    pub fn new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self {
        Self {
            x,
            y,
            width,
            height,
            z_index,
        }
    }

    /// Returns the z-index stacking order value.
    #[must_use]
    pub fn z_index(&self) -> i32 {
        self.z_index
    }

    /// Converts normalized coordinates to pixel values.
    ///
    /// Returns `(x, y, width, height)` in pixels, computed by multiplying
    /// each normalized coordinate by the corresponding output dimension
    /// and rounding to the nearest integer.
    ///
    /// # Arguments
    ///
    /// * `output_width` - Output width in pixels
    /// * `output_height` - Output height in pixels
    #[must_use]
    pub fn to_pixels(&self, output_width: u32, output_height: u32) -> (i32, i32, i32, i32) {
        let w = f64::from(output_width);
        let h = f64::from(output_height);
        (
            (self.x * w).round() as i32,
            (self.y * h).round() as i32,
            (self.width * w).round() as i32,
            (self.height * h).round() as i32,
        )
    }

    /// Validates that all coordinate fields are in the 0.0-1.0 range.
    ///
    /// # Errors
    ///
    /// Returns [`LayoutError::OutOfRange`] if any coordinate is outside 0.0-1.0.
    pub fn validate(&self) -> Result<(), LayoutError> {
        let fields = [
            ("x", self.x),
            ("y", self.y),
            ("width", self.width),
            ("height", self.height),
        ];
        for (name, value) in fields {
            if !(0.0..=1.0).contains(&value) {
                return Err(LayoutError::OutOfRange {
                    field: name.to_string(),
                    value,
                });
            }
        }
        Ok(())
    }
}

#[pymethods]
impl LayoutPosition {
    /// Creates a new LayoutPosition.
    ///
    /// # Arguments
    ///
    /// * `x` - Normalized x coordinate (0.0-1.0)
    /// * `y` - Normalized y coordinate (0.0-1.0)
    /// * `width` - Normalized width (0.0-1.0)
    /// * `height` - Normalized height (0.0-1.0)
    /// * `z_index` - Stacking order (higher values drawn on top)
    #[new]
    fn py_new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self {
        Self::new(x, y, width, height, z_index)
    }

    /// The normalized x coordinate.
    #[getter]
    #[pyo3(name = "x")]
    fn py_x(&self) -> f64 {
        self.x
    }

    /// Sets the normalized x coordinate.
    #[setter]
    #[pyo3(name = "x")]
    fn py_set_x(&mut self, value: f64) {
        self.x = value;
    }

    /// The normalized y coordinate.
    #[getter]
    #[pyo3(name = "y")]
    fn py_y(&self) -> f64 {
        self.y
    }

    /// Sets the normalized y coordinate.
    #[setter]
    #[pyo3(name = "y")]
    fn py_set_y(&mut self, value: f64) {
        self.y = value;
    }

    /// The normalized width.
    #[getter]
    #[pyo3(name = "width")]
    fn py_width(&self) -> f64 {
        self.width
    }

    /// Sets the normalized width.
    #[setter]
    #[pyo3(name = "width")]
    fn py_set_width(&mut self, value: f64) {
        self.width = value;
    }

    /// The normalized height.
    #[getter]
    #[pyo3(name = "height")]
    fn py_height(&self) -> f64 {
        self.height
    }

    /// Sets the normalized height.
    #[setter]
    #[pyo3(name = "height")]
    fn py_set_height(&mut self, value: f64) {
        self.height = value;
    }

    /// The stacking order index.
    #[getter]
    #[pyo3(name = "z_index")]
    fn py_z_index(&self) -> i32 {
        self.z_index
    }

    /// Sets the stacking order index.
    #[setter]
    #[pyo3(name = "z_index")]
    fn py_set_z_index(&mut self, value: i32) {
        self.z_index = value;
    }

    /// Converts normalized coordinates to pixel values.
    ///
    /// Returns a tuple of `(x, y, width, height)` in pixels.
    #[pyo3(name = "to_pixels")]
    fn py_to_pixels(&self, output_width: u32, output_height: u32) -> (i32, i32, i32, i32) {
        self.to_pixels(output_width, output_height)
    }

    /// Validates that all coordinates are in the 0.0-1.0 range.
    ///
    /// Raises LayoutError if any coordinate is out of range.
    #[pyo3(name = "validate")]
    fn py_validate(&self) -> PyResult<()> {
        self.validate()?;
        Ok(())
    }

    fn __repr__(&self) -> String {
        format!(
            "LayoutPosition(x={}, y={}, width={}, height={}, z_index={})",
            self.x, self.y, self.width, self.height, self.z_index
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_construction() {
        let pos = LayoutPosition::new(0.25, 0.5, 0.75, 1.0, 5);
        assert_eq!(pos.x, 0.25);
        assert_eq!(pos.y, 0.5);
        assert_eq!(pos.width, 0.75);
        assert_eq!(pos.height, 1.0);
        assert_eq!(pos.z_index, 5);
    }

    #[test]
    fn test_to_pixels_1920x1080() {
        let pos = LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0);
        assert_eq!(pos.to_pixels(1920, 1080), (0, 0, 1920, 1080));
    }

    #[test]
    fn test_to_pixels_1280x720() {
        let pos = LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0);
        assert_eq!(pos.to_pixels(1280, 720), (640, 360, 640, 360));
    }

    #[test]
    fn test_to_pixels_3840x2160() {
        let pos = LayoutPosition::new(0.25, 0.25, 0.5, 0.5, 0);
        assert_eq!(pos.to_pixels(3840, 2160), (960, 540, 1920, 1080));
    }

    #[test]
    fn test_to_pixels_quarter_screen() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0);
        assert_eq!(pos.to_pixels(1920, 1080), (0, 0, 960, 540));
    }

    #[test]
    fn test_to_pixels_zero() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.0, 0.0, 0);
        assert_eq!(pos.to_pixels(1920, 1080), (0, 0, 0, 0));
    }

    #[test]
    fn test_validate_valid_boundary_zero() {
        let pos = LayoutPosition::new(0.0, 0.0, 0.0, 0.0, 0);
        assert!(pos.validate().is_ok());
    }

    #[test]
    fn test_validate_valid_boundary_one() {
        let pos = LayoutPosition::new(1.0, 1.0, 1.0, 1.0, 0);
        assert!(pos.validate().is_ok());
    }

    #[test]
    fn test_validate_valid_mid_range() {
        let pos = LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0);
        assert!(pos.validate().is_ok());
    }

    #[test]
    fn test_validate_x_too_low() {
        let pos = LayoutPosition::new(-0.1, 0.0, 1.0, 1.0, 0);
        let err = pos.validate().unwrap_err();
        assert_eq!(
            err,
            LayoutError::OutOfRange {
                field: "x".to_string(),
                value: -0.1
            }
        );
    }

    #[test]
    fn test_validate_x_too_high() {
        let pos = LayoutPosition::new(1.1, 0.0, 1.0, 1.0, 0);
        let err = pos.validate().unwrap_err();
        assert_eq!(
            err,
            LayoutError::OutOfRange {
                field: "x".to_string(),
                value: 1.1
            }
        );
    }

    #[test]
    fn test_validate_y_out_of_range() {
        let pos = LayoutPosition::new(0.0, -0.5, 1.0, 1.0, 0);
        let err = pos.validate().unwrap_err();
        assert_eq!(
            err,
            LayoutError::OutOfRange {
                field: "y".to_string(),
                value: -0.5
            }
        );
    }

    #[test]
    fn test_validate_width_out_of_range() {
        let pos = LayoutPosition::new(0.0, 0.0, 2.0, 1.0, 0);
        let err = pos.validate().unwrap_err();
        assert_eq!(
            err,
            LayoutError::OutOfRange {
                field: "width".to_string(),
                value: 2.0
            }
        );
    }

    #[test]
    fn test_validate_height_out_of_range() {
        let pos = LayoutPosition::new(0.0, 0.0, 1.0, -0.01, 0);
        let err = pos.validate().unwrap_err();
        assert_eq!(
            err,
            LayoutError::OutOfRange {
                field: "height".to_string(),
                value: -0.01
            }
        );
    }

    #[test]
    fn test_z_index_negative() {
        let pos = LayoutPosition::new(0.0, 0.0, 1.0, 1.0, -10);
        assert_eq!(pos.z_index, -10);
        assert!(pos.validate().is_ok());
    }

    #[test]
    fn test_display_layout_error() {
        let err = LayoutError::OutOfRange {
            field: "x".to_string(),
            value: 1.5,
        };
        assert_eq!(err.to_string(), "x must be in range 0.0-1.0, got 1.5");
    }

    #[test]
    fn test_repr() {
        let pos = LayoutPosition::new(0.1, 0.2, 0.3, 0.4, 5);
        assert_eq!(
            pos.__repr__(),
            "LayoutPosition(x=0.1, y=0.2, width=0.3, height=0.4, z_index=5)"
        );
    }
}

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn to_pixels_within_bounds(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.0f64..=1.0,
            h in 0.0f64..=1.0,
            z in -100i32..=100,
            out_w in 1u32..=7680,
            out_h in 1u32..=7680,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            let (px, py, pw, ph) = pos.to_pixels(out_w, out_h);
            prop_assert!(px >= 0, "px={px} must be >= 0");
            prop_assert!(py >= 0, "py={py} must be >= 0");
            prop_assert!(pw >= 0, "pw={pw} must be >= 0");
            prop_assert!(ph >= 0, "ph={ph} must be >= 0");
            prop_assert!(px <= out_w as i32, "px={px} must be <= out_w={out_w}");
            prop_assert!(py <= out_h as i32, "py={py} must be <= out_h={out_h}");
            prop_assert!(pw <= out_w as i32, "pw={pw} must be <= out_w={out_w}");
            prop_assert!(ph <= out_h as i32, "ph={ph} must be <= out_h={out_h}");
        }

        #[test]
        fn valid_coords_pass_validation(
            x in 0.0f64..=1.0,
            y in 0.0f64..=1.0,
            w in 0.0f64..=1.0,
            h in 0.0f64..=1.0,
            z in -100i32..=100,
        ) {
            let pos = LayoutPosition::new(x, y, w, h, z);
            prop_assert!(pos.validate().is_ok());
        }
    }
}
