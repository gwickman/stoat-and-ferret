# Time Range Arithmetic

## Goal
Implement operations on time ranges: overlap detection, gap calculation, intersection, and union.

## Requirements

### FR-001: Range Type
- Represent a contiguous time range (start, end)
- Validate start < end
- Support conversion to/from Position pairs

### FR-002: Overlap Detection
- Detect if two ranges overlap
- Return overlap region if they do
- Handle adjacent ranges (no gap, no overlap)

### FR-003: Gap Calculation
- Find gap between two ranges
- Return None if ranges overlap or are adjacent
- Handle ranges in any order

### FR-004: Set Operations
- Intersection of two ranges
- Union of two ranges (if contiguous)
- Difference (range minus another)

### FR-005: List Operations
- Find gaps in a list of ranges
- Merge overlapping ranges in a list
- Calculate total covered duration

## Acceptance Criteria
- [ ] All operations implemented with property tests
- [ ] Edge cases handled (adjacent, contained, disjoint)
- [ ] List operations are efficient (O(n log n))