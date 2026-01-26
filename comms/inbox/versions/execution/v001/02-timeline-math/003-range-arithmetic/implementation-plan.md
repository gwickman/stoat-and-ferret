# Implementation Plan: Range Arithmetic

## Step 1: Define TimeRange
`rust/stoat_ferret_core/src/timeline/range.rs`:
```rust
use super::{Duration, Position};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RangeError {
    InvalidBounds,
}

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

    pub fn duration(&self) -> Duration {
        Duration::between(self.start, self.end).unwrap()
    }
}
```

## Step 2: Overlap Detection
```rust
impl TimeRange {
    pub fn overlaps(&self, other: &TimeRange) -> bool {
        self.start < other.end && other.start < self.end
    }

    pub fn adjacent(&self, other: &TimeRange) -> bool {
        self.end == other.start || other.end == self.start
    }

    pub fn overlap(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) {
            return None;
        }
        let start = std::cmp::max(self.start, other.start);
        let end = std::cmp::min(self.end, other.end);
        Some(TimeRange { start, end })
    }
}
```

## Step 3: Gap Calculation
```rust
impl TimeRange {
    pub fn gap(&self, other: &TimeRange) -> Option<TimeRange> {
        if self.overlaps(other) || self.adjacent(other) {
            return None;
        }
        let (earlier, later) = if self.end <= other.start {
            (self, other)
        } else {
            (other, self)
        };
        TimeRange::new(earlier.end, later.start).ok()
    }
}
```

## Step 4: Set Operations
```rust
impl TimeRange {
    pub fn intersection(&self, other: &TimeRange) -> Option<TimeRange> {
        self.overlap(other)
    }

    pub fn union(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) && !self.adjacent(other) {
            return None;
        }
        Some(TimeRange {
            start: std::cmp::min(self.start, other.start),
            end: std::cmp::max(self.end, other.end),
        })
    }

    pub fn difference(&self, other: &TimeRange) -> Vec<TimeRange> {
        if !self.overlaps(other) {
            return vec![*self];
        }
        let mut result = Vec::new();
        if self.start < other.start {
            if let Ok(r) = TimeRange::new(self.start, other.start) {
                result.push(r);
            }
        }
        if self.end > other.end {
            if let Ok(r) = TimeRange::new(other.end, self.end) {
                result.push(r);
            }
        }
        result
    }
}
```

## Step 5: List Operations
```rust
pub fn find_gaps(ranges: &[TimeRange]) -> Vec<TimeRange> {
    if ranges.is_empty() {
        return vec![];
    }
    let mut sorted: Vec<_> = ranges.to_vec();
    sorted.sort_by_key(|r| r.start);

    let mut gaps = Vec::new();
    let mut current_end = sorted[0].end;

    for range in &sorted[1..] {
        if range.start > current_end {
            if let Ok(gap) = TimeRange::new(current_end, range.start) {
                gaps.push(gap);
            }
        }
        current_end = std::cmp::max(current_end, range.end);
    }
    gaps
}

pub fn merge_ranges(ranges: &[TimeRange]) -> Vec<TimeRange> {
    if ranges.is_empty() {
        return vec![];
    }
    let mut sorted: Vec<_> = ranges.to_vec();
    sorted.sort_by_key(|r| r.start);

    let mut merged = vec![sorted[0]];
    for range in &sorted[1..] {
        let last = merged.last_mut().unwrap();
        if let Some(u) = last.union(range) {
            *last = u;
        } else {
            merged.push(*range);
        }
    }
    merged
}

pub fn total_coverage(ranges: &[TimeRange]) -> Duration {
    let merged = merge_ranges(ranges);
    let total_frames: u64 = merged.iter().map(|r| r.duration().frames()).sum();
    Duration::from_frames(total_frames)
}
```

## Step 6: Property Tests
```rust
proptest! {
    #[test]
    fn overlap_is_symmetric(
        s1 in 0u64..1000, e1 in 1u64..1001,
        s2 in 0u64..1000, e2 in 1u64..1001,
    ) {
        prop_assume!(e1 > s1 && e2 > s2);
        let a = TimeRange::new(Position::from_frames(s1), Position::from_frames(e1)).unwrap();
        let b = TimeRange::new(Position::from_frames(s2), Position::from_frames(e2)).unwrap();
        prop_assert_eq!(a.overlaps(&b), b.overlaps(&a));
    }
}
```

## Verification
- Property tests pass
- Edge cases (adjacent, contained) work correctly
- List operations sort correctly