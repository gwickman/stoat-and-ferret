# C4 Code Level: Layout Module

**Source:** `rust/stoat_ferret_core/src/layout/`
**Component:** Rust Core

## Purpose

Provides normalized coordinate types and predefined layout presets for composition features (PIP, side-by-side, grid layouts). Coordinates are stored normalized (0.0-1.0) for resolution independence and converted to pixels at render time.

## Public Interface

### Structs (PyO3 Classes)

#### `LayoutPosition`
Position and dimensions using normalized coordinates (0.0-1.0).

**Fields:**
- `x: f64` — Normalized x position (0.0-1.0) (PyO3: getter/setter `x`)
- `y: f64` — Normalized y position (0.0-1.0) (PyO3: getter/setter `y`)
- `width: f64` — Normalized width (0.0-1.0) (PyO3: getter/setter `width`)
- `height: f64` — Normalized height (0.0-1.0) (PyO3: getter/setter `height`)
- `z_index: i32` — Stacking order (higher = drawn on top) (PyO3: getter/setter `z_index`)

**Construction:**
- `LayoutPosition::new(x: f64, y: f64, width: f64, height: f64, z_index: i32) -> Self`

**Methods:**
- `z_index() -> i32` — Get stacking order
- `to_pixels(output_width: u32, output_height: u32) -> (i32, i32, i32, i32)` — Convert normalized coords to pixel values
  - Returns `(x_pixels, y_pixels, width_pixels, height_pixels)`
  - Uses `round()` for best-fit mapping
- `validate() -> Result<(), LayoutError>` — Verify all coordinates in 0.0-1.0 range

**PyO3 Methods:**
- `LayoutPosition(x, y, width, height, z_index)` — Constructor
- Properties: `x`, `y`, `width`, `height`, `z_index` with getters/setters
- `to_pixels(output_width: int, output_height: int) -> Tuple[int, int, int, int]`
- `validate() -> None` (raises LayoutError if invalid)

#### `LayoutPreset`
Predefined layout configurations for multi-stream composition.

**Variants:**
- `PipTopLeft` — Picture-in-picture with overlay in top-left corner
- `PipTopRight` — PIP with overlay in top-right corner
- `PipBottomLeft` — PIP with overlay in bottom-left corner
- `PipBottomRight` — PIP with overlay in bottom-right corner
- `SideBySide` — Two inputs split vertically (each 0.5×1.0)
- `TopBottom` — Two inputs stacked horizontally (each 1.0×0.5)
- `Grid2x2` — Four inputs in 2×2 grid (each 0.5×0.5)

**Methods:**
- `positions(input_count: usize) -> Vec<LayoutPosition>` — Generate layout positions
  - `input_count` parameter accepted for forward compatibility but currently unused
  - PIP presets return 2 positions (base layer z_index=0, overlay z_index=1)
  - Tiling presets return fixed count matching layout (2 for Side/Top, 4 for Grid)
  - All positions have 0.0-1.0 coordinates that validate successfully

**PyO3 Methods:**
- `LayoutPreset.pip_top_left` — Factory (as variant)
- `LayoutPreset.pip_top_right`
- `LayoutPreset.pip_bottom_left`
- `LayoutPreset.pip_bottom_right`
- `LayoutPreset.side_by_side`
- `LayoutPreset.top_bottom`
- `LayoutPreset.grid_2x2`
- `positions(input_count: int) -> List[LayoutPosition]` — Instance method

### Enums (PyO3)

#### `LayoutError`
**Variant:**
- `LayoutError::OutOfRange { field: String, value: f64 }`
  - A coordinate field is outside the valid 0.0-1.0 range
  - Display: "{field} must be in range 0.0-1.0, got {value}"

## Preset Specifications

### PIP (Picture-in-Picture) Presets

Structure: Base layer (full-screen, z_index=0) + overlay (quarter-screen, z_index=1)

**PipTopLeft:**
```
Base:    (0.0, 0.0, 1.0, 1.0, z=0)
Overlay: (0.02, 0.02, 0.25, 0.25, z=1)
```

**PipTopRight:**
```
Base:    (0.0, 0.0, 1.0, 1.0, z=0)
Overlay: (0.73, 0.02, 0.25, 0.25, z=1)
```

**PipBottomLeft:**
```
Base:    (0.0, 0.0, 1.0, 1.0, z=0)
Overlay: (0.02, 0.73, 0.25, 0.25, z=1)
```

**PipBottomRight:**
```
Base:    (0.0, 0.0, 1.0, 1.0, z=0)
Overlay: (0.73, 0.73, 0.25, 0.25, z=1)
```

### Tiling Presets

All positions have z_index=0 (no layering, all equal depth).

**SideBySide (2 inputs):**
```
Input 1: (0.0, 0.0, 0.5, 1.0, z=0)
Input 2: (0.5, 0.0, 0.5, 1.0, z=0)
```

**TopBottom (2 inputs):**
```
Input 1: (0.0, 0.0, 1.0, 0.5, z=0)
Input 2: (0.0, 0.5, 1.0, 0.5, z=0)
```

**Grid2x2 (4 inputs):**
```
Input 1 (top-left):     (0.0, 0.0, 0.5, 0.5, z=0)
Input 2 (top-right):    (0.5, 0.0, 0.5, 0.5, z=0)
Input 3 (bottom-left):  (0.0, 0.5, 0.5, 0.5, z=0)
Input 4 (bottom-right): (0.5, 0.5, 0.5, 0.5, z=0)
```

## Dependencies

### Internal Crate Dependencies

None — layout module is self-contained. No dependencies on other crate modules.

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support

## Key Implementation Details

### Normalized Coordinates

All coordinates use normalized values (0.0-1.0) to be resolution-independent:
- (0.0, 0.0) = top-left corner
- (1.0, 1.0) = bottom-right corner
- Width and height as fractions of output dimensions

**Conversion to pixels:**
```rust
pixel_x = round(normalized_x * output_width)
pixel_y = round(normalized_y * output_height)
pixel_width = round(normalized_width * output_width)
pixel_height = round(normalized_height * output_height)
```

Uses `round()` for best-fit mapping. At odd resolutions, may produce 1-pixel asymmetry — expected behavior.

### Z-Index Stacking

- Higher z_index values are drawn on top
- Typically: base layers z_index=0, overlays z_index=1+
- Used during FFmpeg filter graph construction to determine overlay order

### Validation

The `validate()` method checks all coordinate fields:
- x, y, width, height must each be in [0.0, 1.0]
- z_index has no constraints (any i32 valid)
- Returns `Ok(())` if valid, `Err(LayoutError::OutOfRange {...})`  if any field out of range

### Preset Position Count

- PIP presets always return 2 positions (base + overlay)
- SideBySide returns 2 positions
- TopBottom returns 2 positions
- Grid2x2 returns 4 positions

The `input_count` parameter is reserved for future use where presets might adapt to variable input counts.

## Relationships

**Used by:**
- Composition builders (`compose::graph`) — Translate layout positions to FFmpeg overlay/scale filters
- Python UI composition tools — Display and manipulate layout presets
- FFmpeg filter generation — Position overlays using filter parameters

**Uses:**
- (No internal dependencies)

## Testing

Comprehensive test suite with 30+ tests including:

1. **Construction tests** — Create LayoutPosition with various coordinates
2. **Pixel conversion tests:**
   - Full-screen (1920×1080)
   - Half-screen (1280×720)
   - 4K resolution (3840×2160)
   - Quarter screen
   - Zero dimensions

3. **Validation tests:**
   - Valid boundaries (0.0 and 1.0)
   - Out-of-range detection (negative, > 1.0)
   - Each field validation

4. **PIP preset tests:**
   - Each corner variant returns 2 positions
   - Base layer always (0, 0, 1, 1, z=0)
   - Overlay position and z_index correct
   - All positions validate

5. **Tiling preset tests:**
   - SideBySide/TopBottom return 2 positions
   - Grid2x2 returns 4 positions
   - Correct quadrant positions
   - Non-overlapping regions

6. **All presets validation:**
   - Every position from every preset validates

## Notes

- **Asymmetry at Odd Resolutions:** At 1920×1080 with x=0.73, w=0.25: x_pixels=1398 (round(1398.4)). At 1919×1080, x=0.73: x_pixels=1400.87→1401 (off by 1). This is expected and acceptable for video layouts.
- **Resolution-Independent Storage:** Store and transfer normalized coordinates; convert to pixels only when building FFmpeg filters.
- **No Anti-Aliasing:** This is for layout structure only. Anti-aliasing of overlay edges handled by FFmpeg's overlay filter.
- **Z-Index Ordering:** Higher values drawn last (on top). In FFmpeg overlay filter chains, reverse the order of inputs relative to z_index values.

## Example Usage

```python
from stoat_ferret_core import LayoutPreset, LayoutPosition

# Get PIP layout
preset = LayoutPreset.pip_top_left
positions = preset.positions(2)

# positions[0] = base layer (full-screen)
# positions[1] = overlay (quarter-screen top-left, z=1)

# Convert to pixels for 1920×1080 output
for i, pos in enumerate(positions):
    x, y, w, h = pos.to_pixels(1920, 1080)
    print(f"Layer {i}: ({x}, {y}, {w}×{h})")

# Output:
# Layer 0: (0, 0, 1920, 1080)
# Layer 1: (38, 21, 480, 270)
```
