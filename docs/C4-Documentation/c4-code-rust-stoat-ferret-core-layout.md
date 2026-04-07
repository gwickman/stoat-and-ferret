# C4 Code Level: Layout Positioning Module

## Overview

- **Name**: Layout Positioning and Composition Presets
- **Description**: Provides normalized coordinate types and preset layout configurations for multi-stream video composition (PIP, split-screen, grid layouts).
- **Location**: `rust/stoat_ferret_core/src/layout/`
- **Language**: Rust
- **Purpose**: Enables resolution-independent layout positioning with pixel conversion for video composition features.
- **Parent Component**: [Rust Core Engine](./c4-component-rust-core-engine.md)

## Code Elements

### Structs

- `LayoutPosition`
  - Description: Represents a normalized (0.0-1.0) layout position with z-index stacking order, convertible to pixel coordinates. Exported to Python via PyO3.
  - Location: `position.rs:70-76`
  - Fields: `x: f64`, `y: f64`, `width: f64`, `height: f64`, `z_index: i32`
  - Key Methods:
    - `fn new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self`
    - `fn to_pixels(&self, output_width: u32, output_height: u32) -> (i32, i32, i32, i32)` - Converts normalized coordinates to pixel values using rounding
    - `fn validate(&self) -> Result<(), LayoutError>` - Validates all coordinates are in 0.0-1.0 range
    - `fn z_index(&self) -> i32` - Returns stacking order value

### Enums

- `LayoutPreset`
  - Description: Seven predefined layout configurations for PIP (picture-in-picture) and tiling compositions. Each variant generates fixed position vectors with appropriate z-index values.
  - Location: `preset.rs:27-42`
  - Variants: `PipTopLeft`, `PipTopRight`, `PipBottomLeft`, `PipBottomRight`, `SideBySide`, `TopBottom`, `Grid2x2`
  - Key Methods:
    - `fn positions(&self, _input_count: usize) -> Vec<LayoutPosition>` - Returns layout position vector for preset configuration

- `LayoutError`
  - Description: Error type for layout validation failures when coordinates fall outside valid 0.0-1.0 range.
  - Location: `position.rs:14-22`
  - Variant: `OutOfRange { field: String, value: f64 }` - Indicates which coordinate field failed validation

### Python-Exposed Methods (PyO3)

**LayoutPosition PyMethods:**
- `py_new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self`
- `py_x(&self) -> f64` / `py_set_x(&mut self, value: f64)` - x property getter/setter
- `py_y(&self) -> f64` / `py_set_y(&mut self, value: f64)` - y property getter/setter
- `py_width(&self) -> f64` / `py_set_width(&mut self, value: f64)` - width property getter/setter
- `py_height(&self) -> f64` / `py_set_height(&mut self, value: f64)` - height property getter/setter
- `py_z_index(&self) -> i32` / `py_set_z_index(&mut self, value: i32)` - z_index property getter/setter
- `py_to_pixels(&self, output_width: u32, output_height: u32) -> (i32, i32, i32, i32)` - Pixel conversion
- `py_validate(&self) -> PyResult<()>` - Validation with Python error propagation
- `__repr__(&self) -> String` - String representation

**LayoutPreset PyMethods:**
- `py_positions(&self, input_count: usize) -> Vec<LayoutPosition>` - Returns preset positions

## Dependencies

### Internal Dependencies
- `super::position::LayoutPosition` (used by preset.rs)

### External Dependencies
- `pyo3::prelude::*` - PyO3 Python binding framework
- `pyo3_stub_gen::derive::gen_stub_pyclass` - Stub generation for type checking
- `std::fmt` - Display trait implementation

## Relationships

```mermaid
---
title: Code Diagram for Layout Module
---
classDiagram
    namespace LayoutModule {
        class LayoutPosition {
            -x: f64
            -y: f64
            -width: f64
            -height: f64
            -z_index: i32
            +new(x, y, width, height, z_index) LayoutPosition
            +z_index() i32
            +to_pixels(output_width, output_height) (i32, i32, i32, i32)
            +validate() Result
        }
        
        class LayoutError {
            <<enum>>
            OutOfRange {field: String, value: f64}
            +to_string() String
        }
        
        class LayoutPreset {
            <<enum>>
            PipTopLeft
            PipTopRight
            PipBottomLeft
            PipBottomRight
            SideBySide
            TopBottom
            Grid2x2
            +positions(input_count) Vec~LayoutPosition~
        }
    }

    LayoutError --|> LayoutPosition : validation errors
    LayoutPreset --|> LayoutPosition : creates positions
    LayoutPosition : Uses rounding for pixel conversion
    LayoutError : Implements Display, Error traits
```

## Notes

- **Normalized Coordinates**: All coordinates use 0.0-1.0 range for resolution independence. Pixel conversion uses `round()`, which may produce 1-pixel asymmetry at odd resolutions — this is expected behavior.
- **Z-Index Stacking**: The `z_index` field controls render order (higher values drawn on top). PIP presets use z_index=0 for base, z_index=1 for overlay; tiling presets use z_index=0 for all.
- **Python Interop**: Fully exported to Python via PyO3 with property getters/setters matching Rust struct fields. PyO3 name attributes control Python naming convention.
- **Validation**: All presets' positions validate successfully (0.0-1.0 range enforced). User-created positions must call `validate()` before use.
- **Preset Behavior**: The `input_count` parameter in `positions()` is reserved for future use; currently all presets return fixed position counts regardless.
