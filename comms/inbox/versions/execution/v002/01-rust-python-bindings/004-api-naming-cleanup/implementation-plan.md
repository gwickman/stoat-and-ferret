# Implementation Plan: API Naming Cleanup

**Execution Order: LAST in Theme 01**

## Step 1: Audit py_ Methods
Run grep to find all py_ methods:
```bash
grep -rn "fn py_" rust/stoat_ferret_core/src/
```

Check each for #[pyo3(name = "...")] attribute.

## Step 2: Identify Methods Missing Name Attribute
Look for patterns like:
```rust
#[pymethods]
impl Foo {
    fn py_something(&self) -> ... {  // Missing name attribute!
```

Should be:
```rust
    #[pyo3(name = "something")]
    fn py_something(&self) -> ... {
```

## Step 3: Fix Missing Attributes
Add name attribute to any method exposing py_ prefix.

Common locations to check (from exploration):
- timeline/position.rs (py_frames, py_new)
- timeline/duration.rs (py_frames, py_new)
- timeline/framerate.rs (py_numerator, py_denominator, py_new)
- timeline/range.rs (py_start, py_end, py_duration, py_overlaps, py_union, etc.)
- ffmpeg/command.rs (py_new, py_input, py_output, py_build, etc.)
- ffmpeg/filter.rs (py_new, py_param, py_filter, etc.)

## Step 4: Update Tests (~20 assertions)
Replace all py_ references in tests:

```python
# Before
assert pos.py_frames == 100
assert range.py_overlaps(other)
assert range.py_start.py_frames == 10

# After  
assert pos.frames == 100
assert range.overlaps(other)
assert range.start.frames == 10
```

Track all changes:
1. Position: py_frames → frames
2. Duration: py_frames → frames
3. FrameRate: py_numerator → numerator, py_denominator → denominator
4. TimeRange: py_start → start, py_end → end, py_duration → duration
5. TimeRange: py_overlaps → overlaps, py_union → union, etc.

## Step 5: Regenerate Stubs
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

Verify stubs show clean names.

## Step 6: Update Export List
Edit TestModuleExports.test_all_exports_present:
```python
expected = [
    # Utility
    "health_check",
    # Timeline types
    "FrameRate",
    "Position",
    "Duration",
    "TimeRange",
    # Clip types (new in v002)
    "Clip",
    "ValidationError",
    "validate_clip",
    # Range operations (new in v002)
    "find_gaps",
    "merge_ranges",
    "total_coverage",
    # FFmpeg command building
    "FFmpegCommand",
    "Filter",
    "FilterChain",
    "FilterGraph",
    # Filter helpers
    "scale_filter",
    "concat_filter",
    # Sanitization functions
    "escape_filter_text",
    "validate_path",
    "validate_crf",
    "validate_speed",
    "validate_volume",
    "validate_video_codec",
    "validate_audio_codec",
    "validate_preset",
    # Exceptions
    "CommandError",
    "SanitizationError",
]
```

## Step 7: Full Test Run
```bash
uv run pytest tests/ -v
uv run mypy src/
```

## Verification
- No test uses py_ prefix
- `dir(stoat_ferret_core.Position)` shows no py_ methods
- All tests pass
- TestModuleExports passes with updated list