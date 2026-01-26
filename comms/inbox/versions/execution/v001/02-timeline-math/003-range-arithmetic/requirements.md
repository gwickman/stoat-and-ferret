# Time Range Arithmetic

## Goal
Implement operations on time ranges: overlap detection, gap calculation, intersection, and union.

## Requirements

### FR-001: TimeRange Type
- Represent a contiguous time range (start, end)
- Validate start < end on construction
- Half-open interval: [start, end)

### FR-002: Overlap Detection
- Detect if two ranges overlap
- Return overlap region if they do
- Handle adjacent ranges (no gap, no overlap)

### FR-003: Gap Calculation
- Find gap between two non-overlapping ranges
- Return None if ranges overlap or are adjacent
- Handle ranges in any order

### FR-004: Set Operations
- Intersection of two ranges
- Union of two ranges (if contiguous)
- Difference (range minus another) - may return 0, 1, or 2 ranges

### FR-005: List Operations
- Find gaps in a list of ranges
- Merge overlapping/adjacent ranges in a list
- Calculate total covered duration

## Acceptance Criteria
- [ ] All operations implemented with property tests
- [ ] Edge cases handled (adjacent, contained, disjoint)
- [ ] List operations are efficient (O(n log n))