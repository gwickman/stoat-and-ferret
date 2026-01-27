---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  cargo_test: pass
  cargo_clippy: pass
---
# Completion Report: 004-api-naming-cleanup

## Summary

Successfully cleaned up all Python-visible API names to remove `py_` prefixes, ensuring a clean and Pythonic API surface for users of the `stoat_ferret_core` module.

## Changes Made

### Rust Code (5 files)

1. **timeline/position.rs** - Added `#[pyo3(name = "frames")]` to `py_frames` getter
2. **timeline/duration.rs** - Added `#[pyo3(name = "frames")]` to `py_frames` getter
3. **timeline/framerate.rs** - Added `#[pyo3(name = "numerator")]` and `#[pyo3(name = "denominator")]` to getters
4. **timeline/range.rs** - Added name attributes to 11 methods:
   - Getters: `start`, `end`, `duration`
   - Methods: `overlaps`, `adjacent`, `overlap`, `gap`, `intersection`, `union`, `difference`
5. **clip/validation.rs** - Added name attributes to 2 functions:
   - `validate_clip` (was `py_validate_clip`)
   - `validate_clips` (was `py_validate_clips`)

**Total: 16 methods fixed**

### Test Updates (1 file)

Updated `tests/test_pyo3_bindings.py` with **37 assertion changes**:
- `rate.py_numerator` → `rate.numerator`
- `rate.py_denominator` → `rate.denominator`
- `.py_frames` → `.frames` (28 occurrences)
- `.py_start` → `.start` (4 occurrences)
- `.py_end` → `.end` (4 occurrences)
- `.py_duration` → `.duration` (3 occurrences across different contexts)
- `.py_overlaps()` → `.overlaps()` (2 occurrences)
- `.py_union()` → `.union()` (1 occurrence)
- `py_validate_clip` → `validate_clip` (5 occurrences)
- `py_validate_clips` → `validate_clips` (2 occurrences)

### Stub Updates (3 files)

1. **stubs/stoat_ferret_core/_core.pyi** - Updated function names
2. **stubs/stoat_ferret_core/__init__.pyi** - Updated exports
3. **src/stoat_ferret_core/_core.pyi** - Updated auto-generated stub + added exception types

### Python Module Updates (1 file)

- **src/stoat_ferret_core/__init__.py** - Updated imports and exports

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| No py_ prefixes visible from Python | ✅ PASS |
| All ~20 test assertions updated | ✅ PASS (37 updated) |
| Stubs show clean method names | ✅ PASS |
| TestModuleExports passes with complete list | ✅ PASS |

## Quality Gates

| Gate | Result |
|------|--------|
| ruff check | ✅ PASS |
| mypy src | ✅ PASS |
| pytest (73 tests) | ✅ PASS |
| cargo test (201 tests) | ✅ PASS |
| cargo clippy | ✅ PASS |
| cargo doc-test (83 tests) | ✅ PASS |

## Test Results

- **Python tests**: 73 passed
- **Rust unit tests**: 201 passed
- **Rust doc tests**: 83 passed

## API Surface After Cleanup

All TimeRange methods now have clean Python names:
```python
from stoat_ferret_core import TimeRange, Position, validate_clip, validate_clips

# Clean property names
range_.start      # was: range_.py_start
range_.end        # was: range_.py_end
range_.duration   # was: range_.py_duration

# Clean method names
range_.overlaps(other)     # was: range_.py_overlaps(other)
range_.adjacent(other)     # was: range_.py_adjacent(other)
range_.overlap(other)      # was: range_.py_overlap(other)
range_.gap(other)          # was: range_.py_gap(other)
range_.intersection(other) # was: range_.py_intersection(other)
range_.union(other)        # was: range_.py_union(other)
range_.difference(other)   # was: range_.py_difference(other)

# Clean function names
validate_clip(clip)   # was: py_validate_clip(clip)
validate_clips(clips) # was: py_validate_clips(clips)
```
