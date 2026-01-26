# Filter Chain Builder

## Goal
Build FFmpeg filter chains (-filter_complex) for common operations: concat, scale, pad, format.

## Requirements

### FR-001: Filter Graph Basics
- Generate -filter_complex argument value
- Support named inputs [0:v], [0:a]
- Support named outputs [outv], [outa]
- Chain filters with commas, separate chains with semicolons

### FR-002: Concat Filter
- Concatenate multiple inputs
- Specify stream count (n), video streams (v), audio streams (a)

### FR-003: Scale Filter
- Scale to specific dimensions
- Maintain aspect ratio option (force_original_aspect_ratio)
- Support -1 for auto-calculate dimension

### FR-004: Pad Filter
- Add padding to reach target dimensions
- Center content with (ow-iw)/2, (oh-ih)/2
- Specify pad color

### FR-005: Format Filter
- Convert pixel format
- Support common formats (yuv420p, rgb24)

### FR-006: Filter Chaining
- Connect multiple filters in sequence
- Builder pattern for filter graph construction

## Acceptance Criteria
- [ ] Filter strings are valid FFmpeg syntax
- [ ] Concat works with multiple inputs
- [ ] Scale/pad generate correct parameters
- [ ] Filter chains connect properly