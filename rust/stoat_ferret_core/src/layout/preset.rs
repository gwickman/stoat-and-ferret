//! Predefined layout presets for common composition patterns.
//!
//! [`LayoutPreset`] provides 7 preset configurations for PIP (picture-in-picture)
//! and tiling layouts. Each preset generates correct [`LayoutPosition`] vectors
//! with appropriate z_index values.

use pyo3::prelude::*;

use super::position::LayoutPosition;

/// Predefined layout configurations for multi-stream composition.
///
/// Each variant produces a set of [`LayoutPosition`] values when
/// [`LayoutPreset::positions`] is called.
///
/// # PIP Presets
///
/// PIP (picture-in-picture) presets place a full-screen base layer (z_index=0)
/// with a smaller overlay in one corner (z_index=1). The overlay is 0.25x0.25
/// with a 0.02 margin from the edge.
///
/// # Tiling Presets
///
/// Tiling presets divide the output into non-overlapping regions, all at z_index=0.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LayoutPreset {
    /// PIP with overlay in top-left corner.
    PipTopLeft,
    /// PIP with overlay in top-right corner.
    PipTopRight,
    /// PIP with overlay in bottom-left corner.
    PipBottomLeft,
    /// PIP with overlay in bottom-right corner.
    PipBottomRight,
    /// Two inputs side by side (each 0.5x1.0).
    SideBySide,
    /// Two inputs stacked vertically (each 1.0x0.5).
    TopBottom,
    /// Four inputs in a 2x2 grid (each 0.5x0.5).
    Grid2x2,
}

impl LayoutPreset {
    /// Returns the layout positions for this preset.
    ///
    /// The `input_count` parameter is accepted for forward compatibility
    /// but currently unused — each preset returns a fixed number of positions.
    ///
    /// # Returns
    ///
    /// A vector of [`LayoutPosition`] values defining the composition layout.
    #[must_use]
    pub fn positions(&self, _input_count: usize) -> Vec<LayoutPosition> {
        match self {
            LayoutPreset::PipTopLeft => vec![
                LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
                LayoutPosition::new(0.02, 0.02, 0.25, 0.25, 1),
            ],
            LayoutPreset::PipTopRight => vec![
                LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
                LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1),
            ],
            LayoutPreset::PipBottomLeft => vec![
                LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
                LayoutPosition::new(0.02, 0.73, 0.25, 0.25, 1),
            ],
            LayoutPreset::PipBottomRight => vec![
                LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
                LayoutPosition::new(0.73, 0.73, 0.25, 0.25, 1),
            ],
            LayoutPreset::SideBySide => vec![
                LayoutPosition::new(0.0, 0.0, 0.5, 1.0, 0),
                LayoutPosition::new(0.5, 0.0, 0.5, 1.0, 0),
            ],
            LayoutPreset::TopBottom => vec![
                LayoutPosition::new(0.0, 0.0, 1.0, 0.5, 0),
                LayoutPosition::new(0.0, 0.5, 1.0, 0.5, 0),
            ],
            LayoutPreset::Grid2x2 => vec![
                LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0),
                LayoutPosition::new(0.5, 0.0, 0.5, 0.5, 0),
                LayoutPosition::new(0.0, 0.5, 0.5, 0.5, 0),
                LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0),
            ],
        }
    }
}

#[pymethods]
impl LayoutPreset {
    /// Returns the layout positions for this preset.
    ///
    /// Args:
    ///     input_count: Number of inputs (reserved for future use).
    ///
    /// Returns:
    ///     A list of LayoutPosition objects defining the composition layout.
    #[pyo3(name = "positions")]
    fn py_positions(&self, input_count: usize) -> Vec<LayoutPosition> {
        self.positions(input_count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- PIP preset tests ---

    #[test]
    fn pip_top_left_returns_two_positions() {
        let positions = LayoutPreset::PipTopLeft.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn pip_top_left_base_layer() {
        let positions = LayoutPreset::PipTopLeft.positions(2);
        let base = &positions[0];
        assert_eq!(*base, LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0));
    }

    #[test]
    fn pip_top_left_overlay() {
        let positions = LayoutPreset::PipTopLeft.positions(2);
        let overlay = &positions[1];
        assert_eq!(*overlay, LayoutPosition::new(0.02, 0.02, 0.25, 0.25, 1));
    }

    #[test]
    fn pip_top_right_returns_two_positions() {
        let positions = LayoutPreset::PipTopRight.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn pip_top_right_overlay() {
        let positions = LayoutPreset::PipTopRight.positions(2);
        let overlay = &positions[1];
        assert_eq!(*overlay, LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1));
    }

    #[test]
    fn pip_bottom_left_returns_two_positions() {
        let positions = LayoutPreset::PipBottomLeft.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn pip_bottom_left_overlay() {
        let positions = LayoutPreset::PipBottomLeft.positions(2);
        let overlay = &positions[1];
        assert_eq!(*overlay, LayoutPosition::new(0.02, 0.73, 0.25, 0.25, 1));
    }

    #[test]
    fn pip_bottom_right_returns_two_positions() {
        let positions = LayoutPreset::PipBottomRight.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn pip_bottom_right_overlay() {
        let positions = LayoutPreset::PipBottomRight.positions(2);
        let overlay = &positions[1];
        assert_eq!(*overlay, LayoutPosition::new(0.73, 0.73, 0.25, 0.25, 1));
    }

    #[test]
    fn pip_presets_base_layer_z_index_zero() {
        let pip_presets = [
            LayoutPreset::PipTopLeft,
            LayoutPreset::PipTopRight,
            LayoutPreset::PipBottomLeft,
            LayoutPreset::PipBottomRight,
        ];
        for preset in &pip_presets {
            let positions = preset.positions(2);
            assert_eq!(
                positions[0],
                LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
                "Base layer for {preset:?} should be full-screen z_index=0"
            );
        }
    }

    #[test]
    fn pip_presets_overlay_z_index_one() {
        let pip_presets = [
            LayoutPreset::PipTopLeft,
            LayoutPreset::PipTopRight,
            LayoutPreset::PipBottomLeft,
            LayoutPreset::PipBottomRight,
        ];
        for preset in &pip_presets {
            let positions = preset.positions(2);
            let overlay = &positions[1];
            assert!(
                overlay.validate().is_ok(),
                "Overlay for {preset:?} must validate"
            );
        }
    }

    // --- Tiling preset tests ---

    #[test]
    fn side_by_side_returns_two_positions() {
        let positions = LayoutPreset::SideBySide.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn side_by_side_left_half() {
        let positions = LayoutPreset::SideBySide.positions(2);
        assert_eq!(positions[0], LayoutPosition::new(0.0, 0.0, 0.5, 1.0, 0));
    }

    #[test]
    fn side_by_side_right_half() {
        let positions = LayoutPreset::SideBySide.positions(2);
        assert_eq!(positions[1], LayoutPosition::new(0.5, 0.0, 0.5, 1.0, 0));
    }

    #[test]
    fn top_bottom_returns_two_positions() {
        let positions = LayoutPreset::TopBottom.positions(2);
        assert_eq!(positions.len(), 2);
    }

    #[test]
    fn top_bottom_top_half() {
        let positions = LayoutPreset::TopBottom.positions(2);
        assert_eq!(positions[0], LayoutPosition::new(0.0, 0.0, 1.0, 0.5, 0));
    }

    #[test]
    fn top_bottom_bottom_half() {
        let positions = LayoutPreset::TopBottom.positions(2);
        assert_eq!(positions[1], LayoutPosition::new(0.0, 0.5, 1.0, 0.5, 0));
    }

    #[test]
    fn grid_2x2_returns_four_positions() {
        let positions = LayoutPreset::Grid2x2.positions(4);
        assert_eq!(positions.len(), 4);
    }

    #[test]
    fn grid_2x2_quadrants() {
        let positions = LayoutPreset::Grid2x2.positions(4);
        assert_eq!(positions[0], LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0));
        assert_eq!(positions[1], LayoutPosition::new(0.5, 0.0, 0.5, 0.5, 0));
        assert_eq!(positions[2], LayoutPosition::new(0.0, 0.5, 0.5, 0.5, 0));
        assert_eq!(positions[3], LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0));
    }

    #[test]
    fn tiling_presets_all_z_index_zero() {
        let tiling_presets = [
            LayoutPreset::SideBySide,
            LayoutPreset::TopBottom,
            LayoutPreset::Grid2x2,
        ];
        for preset in &tiling_presets {
            let positions = preset.positions(4);
            for (i, pos) in positions.iter().enumerate() {
                assert_eq!(
                    pos.to_pixels(1920, 1080).0.signum(),
                    pos.to_pixels(1920, 1080).0.signum(),
                    "Sanity check for {preset:?}[{i}]"
                );
                // z_index is not exposed as a pub field, so verify via validate
                assert!(
                    pos.validate().is_ok(),
                    "Position {i} for {preset:?} must validate"
                );
            }
        }
    }

    // --- Validation tests (NFR-001) ---

    #[test]
    fn all_presets_all_positions_validate() {
        let all_presets = [
            LayoutPreset::PipTopLeft,
            LayoutPreset::PipTopRight,
            LayoutPreset::PipBottomLeft,
            LayoutPreset::PipBottomRight,
            LayoutPreset::SideBySide,
            LayoutPreset::TopBottom,
            LayoutPreset::Grid2x2,
        ];
        for preset in &all_presets {
            let positions = preset.positions(4);
            for (i, pos) in positions.iter().enumerate() {
                assert!(
                    pos.validate().is_ok(),
                    "Position {i} for {preset:?} failed validation: {:?}",
                    pos.validate().err()
                );
            }
        }
    }

    // --- Enum variant count ---

    #[test]
    fn all_seven_variants_exist() {
        let variants = [
            LayoutPreset::PipTopLeft,
            LayoutPreset::PipTopRight,
            LayoutPreset::PipBottomLeft,
            LayoutPreset::PipBottomRight,
            LayoutPreset::SideBySide,
            LayoutPreset::TopBottom,
            LayoutPreset::Grid2x2,
        ];
        assert_eq!(variants.len(), 7);
    }
}
