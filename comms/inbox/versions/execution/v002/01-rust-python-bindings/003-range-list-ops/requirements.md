# TimeRange List Operations

## Goal
Expose find_gaps, merge_ranges, and total_coverage functions to Python.

## Background
These functions exist in rust/stoat_ferret_core/src/timeline/range.rs:
- find_gaps(ranges) -> Vec<TimeRange>
- merge_ranges(ranges) -> Vec<TimeRange>  
- total_coverage(ranges) -> Duration

None are currently exposed to Python.

**Evidence:** `comms/outbox/exploration/design-research-gaps/rust-types.md`

## Requirements

### FR-001: Expose find_gaps
- Add #[pyfunction] to find_gaps
- Accept list of TimeRange, return list of TimeRange
- Register in lib.rs

### FR-002: Expose merge_ranges
- Add #[pyfunction] to merge_ranges
- Accept list of TimeRange, return list of TimeRange
- Register in lib.rs

### FR-003: Expose total_coverage
- Add #[pyfunction] to total_coverage
- Accept list of TimeRange, return Duration
- Register in lib.rs

### FR-004: Regenerate Stubs
- Stubs must include new functions

### FR-005: Integration Tests
- Test each function with various inputs
- Test edge cases (empty list, single range, overlapping ranges)

## Acceptance Criteria
- [ ] `from stoat_ferret_core import find_gaps, merge_ranges, total_coverage`
- [ ] find_gaps returns gaps between ranges
- [ ] merge_ranges combines overlapping/adjacent ranges
- [ ] total_coverage returns total duration (overlaps counted once)
- [ ] Stubs updated
- [ ] Integration tests pass