# Implementation Plan: Range List Operations

## Step 1: Add PyO3 to Functions
Edit `rust/stoat_ferret_core/src/timeline/range.rs`:

```rust
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyfunction;

#[gen_stub_pyfunction]
#[pyfunction]
pub fn find_gaps(ranges: Vec<TimeRange>) -> Vec<TimeRange> {
    // Call existing implementation (may need to adapt from slice)
    find_gaps_impl(&ranges)
}

#[gen_stub_pyfunction]
#[pyfunction]
pub fn merge_ranges(ranges: Vec<TimeRange>) -> Vec<TimeRange> {
    merge_ranges_impl(&ranges)
}

#[gen_stub_pyfunction]
#[pyfunction]
pub fn total_coverage(ranges: Vec<TimeRange>) -> Duration {
    total_coverage_impl(&ranges)
}
```

## Step 2: Register in lib.rs
```rust
// In _core module registration
m.add_function(wrap_pyfunction!(timeline::range::find_gaps, m)?)?;
m.add_function(wrap_pyfunction!(timeline::range::merge_ranges, m)?)?;
m.add_function(wrap_pyfunction!(timeline::range::total_coverage, m)?)?;
```

## Step 3: Regenerate Stubs
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

## Step 4: Add Integration Tests
Add to `tests/test_pyo3_bindings.py`:

```python
class TestRangeListOperations:
    def test_find_gaps_basic(self):
        from stoat_ferret_core import Position, TimeRange, find_gaps
        ranges = [
            TimeRange(Position(0), Position(10)),
            TimeRange(Position(20), Position(30)),
        ]
        gaps = find_gaps(ranges)
        assert len(gaps) == 1
        assert gaps[0].start.frames == 10
        assert gaps[0].end.frames == 20

    def test_find_gaps_empty(self):
        from stoat_ferret_core import find_gaps
        gaps = find_gaps([])
        assert gaps == []

    def test_merge_ranges_overlapping(self):
        from stoat_ferret_core import Position, TimeRange, merge_ranges
        ranges = [
            TimeRange(Position(0), Position(15)),
            TimeRange(Position(10), Position(25)),
        ]
        merged = merge_ranges(ranges)
        assert len(merged) == 1
        assert merged[0].start.frames == 0
        assert merged[0].end.frames == 25

    def test_merge_ranges_adjacent(self):
        from stoat_ferret_core import Position, TimeRange, merge_ranges
        ranges = [
            TimeRange(Position(0), Position(10)),
            TimeRange(Position(10), Position(20)),
        ]
        merged = merge_ranges(ranges)
        assert len(merged) == 1
        assert merged[0].end.frames == 20

    def test_total_coverage_with_overlap(self):
        from stoat_ferret_core import Position, TimeRange, total_coverage
        ranges = [
            TimeRange(Position(0), Position(10)),
            TimeRange(Position(5), Position(15)),  # overlaps by 5
        ]
        total = total_coverage(ranges)
        assert total.frames == 15  # 0-15, not 20

    def test_total_coverage_empty(self):
        from stoat_ferret_core import Duration, total_coverage
        total = total_coverage([])
        assert total.frames == 0
```

## Step 5: Update TestModuleExports
Add to expected exports:
- `find_gaps`
- `merge_ranges`
- `total_coverage`

## Verification
- `cargo test` passes
- `uv run pytest tests/test_pyo3_bindings.py::TestRangeListOperations -v` passes