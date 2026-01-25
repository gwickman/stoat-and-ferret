# Implementation Plan: Range Arithmetic

## Step 1: Define TimeRange Type
Create `rust/stoat_ferret_core/src/timeline/range.rs`:

```rust
use super::{Position, Duration};

/// A contiguous time range [start, end)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TimeRange {
    start: Position,
    end: Position,
}

impl TimeRange {
    pub fn new(start: Position, end: Position) -> Result<Self, RangeError> {
        if end <= start {
            return Err(RangeError::InvalidBounds);
        }
        Ok(Self { start, end })
    }

    pub fn start(&self) -> Position { self.start }
    pub fn end(&self) -> Position { self.end }
    pub fn duration(&self) -> Duration { Duration::between(self.start, self.end).unwrap() }
}
```

## Step 2: Implement Overlap Detection
```rust
impl TimeRange {
    /// Check if ranges overlap (share any points)
    pub fn overlaps(&self, other: &TimeRange) -> bool {
        self.start < other.end && other.start < self.end
    }

    /// Check if ranges are adjacent (touch but don't overlap)
    pub fn adjacent(&self, other: &TimeRange) -> bool {
        self.end == other.start || other.end == self.start
    }

    /// Get the overlapping region, if any
    pub fn overlap(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) {
            return None;
        }
        let start = self.start.max(other.start);
        let end = self.end.min(other.end);
        Some(TimeRange { start, end })
    }
}
```

## Step 3: Implement Gap Calculation
```rust
impl TimeRange {
    /// Get the gap between two non-overlapping ranges
    pub fn gap(&self, other: &TimeRange) -> Option<TimeRange> {
        if self.overlaps(other) || self.adjacent(other) {
            return None;
        }
        let (earlier, later) = if self.end <= other.start {
            (self, other)
        } else {
            (other, self)
        };
        Some(TimeRange {
            start: earlier.end,
            end: later.start,
        })
    }
}
```

## Step 4: Implement Set Operations
```rust
impl TimeRange {
    /// Intersection (same as overlap)
    pub fn intersection(&self, other: &TimeRange) -> Option<TimeRange> {
        self.overlap(other)
    }

    /// Union if ranges are contiguous (overlap or adjacent)
    pub fn union(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) && !self.adjacent(other) {
            return None;
        }
        Some(TimeRange {
            start: self.start.min(other.start),
            end: self.end.max(other.end),
        })
    }

    /// Subtract other from self (may return 0, 1, or 2 ranges)
    pub fn difference(&self, other: &TimeRange) -> Vec<TimeRange> {
        // Implementation handles contained, partial overlap, disjoint
        ...
    }
}
```

## Step 5: Implement List Operations
```rust
/// Find all gaps in a list of ranges
pub fn find_gaps(ranges: &[TimeRange]) -> Vec<TimeRange> {
    if ranges.is_empty() { return vec![]; }
    let mut sorted: Vec<_> = ranges.to_vec();
    sorted.sort_by_key(|r| r.start);
    
    let mut gaps = Vec::new();
    let mut current_end = sorted[0].end;
    
    for range in &sorted[1..] {
        if range.start > current_end {
            gaps.push(TimeRange::new(current_end, range.start).unwrap());
        }
        current_end = current_end.max(range.end);
    }
    gaps
}

/// Merge overlapping/adjacent ranges
pub fn merge_ranges(ranges: &[TimeRange]) -> Vec<TimeRange> { ... }

/// Total duration covered by ranges
pub fn total_coverage(ranges: &[TimeRange]) -> Duration { ... }
```

## Step 6: Property Tests
```rust
proptest! {
    #[test]
    fn overlap_is_symmetric(a: TimeRange, b: TimeRange) {
        prop_assert_eq!(a.overlaps(&b), b.overlaps(&a));
    }

    #[test]
    fn union_contains_both(a: TimeRange, b: TimeRange) {
        if let Some(u) = a.union(&b) {
            prop_assert!(u.start <= a.start && u.end >= a.end);
            prop_assert!(u.start <= b.start && u.end >= b.end);
        }
    }
}
```

## Verification
- Property tests pass
- Edge cases (adjacent, contained) work correctly
- List operations sort correctly