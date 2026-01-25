# Filter Chain Builder

## Goal
Build FFmpeg filter chains (-filter_complex) for common operations: concat, scale, pad, format.

## Requirements

### FR-001: Filter Graph Basics
- Generate -filter_complex argument
- Support named inputs [0:v], [0:a]
- Support named outputs [outv], [outa]
- Chain filters with semicolons

### FR-002: Concat Filter
- Concatenate multiple inputs
- Specify stream count (video, audio)
- Handle inputs with different formats

### FR-003: Scale Filter
- Scale to specific dimensions
- Maintain aspect ratio options
- Support common presets (720p, 1080p)

### FR-004: Pad Filter
- Add padding to reach target dimensions
- Center content in padded frame
- Specify pad color

### FR-005: Format Filter
- Convert pixel format
- Support common formats (yuv420p, rgb24)

### FR-006: Filter Chaining
- Connect multiple filters in sequence
- Automatic intermediate label generation
- Builder pattern for filter construction

## Acceptance Criteria
- [ ] Filter strings are valid FFmpeg syntax
- [ ] Concat works with multiple inputs
- [ ] Scale/pad preserve or modify aspect ratio correctly
- [ ] Filter chains connect properly