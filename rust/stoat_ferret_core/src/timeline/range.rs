//! Time range representation and arithmetic.
//!
//! This module provides a [`TimeRange`] type that represents a contiguous time range
//! on a timeline as a half-open interval [start, end), along with operations for
//! overlap detection, gap calculation, and set operations.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::{Duration, Position};

/// Error type for time range operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RangeError {
    /// The end position is not greater than the start position.
    InvalidBounds,
}

impl std::fmt::Display for RangeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RangeError::InvalidBounds => {
                write!(f, "invalid bounds: end must be greater than start")
            }
        }
    }
}

impl std::error::Error for RangeError {}

/// A contiguous time range represented as a half-open interval [start, end).
///
/// The range includes the start position but excludes the end position.
/// This representation is standard for video editing as it allows ranges
/// to be concatenated without overlap or gaps.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{TimeRange, Position};
///
/// // Create a range from frame 10 to frame 20
/// let start = Position::from_frames(10);
/// let end = Position::from_frames(20);
/// let range = TimeRange::new(start, end).unwrap();
///
/// assert_eq!(range.start().frames(), 10);
/// assert_eq!(range.end().frames(), 20);
/// assert_eq!(range.duration().frames(), 10);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TimeRange {
    start: Position,
    end: Position,
}

impl TimeRange {
    /// Creates a new time range from start and end positions.
    ///
    /// Returns an error if `end <= start`.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position (inclusive)
    /// * `end` - The end position (exclusive)
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let range = TimeRange::new(
    ///     Position::from_frames(0),
    ///     Position::from_frames(100),
    /// ).unwrap();
    ///
    /// // Invalid: end <= start
    /// let invalid = TimeRange::new(
    ///     Position::from_frames(100),
    ///     Position::from_frames(50),
    /// );
    /// assert!(invalid.is_err());
    /// ```
    pub fn new(start: Position, end: Position) -> Result<Self, RangeError> {
        if end <= start {
            return Err(RangeError::InvalidBounds);
        }
        Ok(Self { start, end })
    }

    /// Returns the start position of the range.
    #[must_use]
    pub fn start(&self) -> Position {
        self.start
    }

    /// Returns the end position of the range.
    #[must_use]
    pub fn end(&self) -> Position {
        self.end
    }

    /// Returns the duration of the range.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let range = TimeRange::new(
    ///     Position::from_frames(10),
    ///     Position::from_frames(30),
    /// ).unwrap();
    /// assert_eq!(range.duration().frames(), 20);
    /// ```
    #[must_use]
    pub fn duration(&self) -> Duration {
        // Safe to unwrap: we guarantee end > start in the constructor
        Duration::between(self.start, self.end).unwrap()
    }

    /// Checks if this range overlaps with another range.
    ///
    /// Two ranges overlap if they share at least one frame in common.
    /// Adjacent ranges (where one ends where another begins) do not overlap.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap();
    /// let c = TimeRange::new(Position::from_frames(10), Position::from_frames(20)).unwrap();
    ///
    /// assert!(a.overlaps(&b));  // Overlap: frames 5-10
    /// assert!(!a.overlaps(&c)); // Adjacent: no overlap
    /// ```
    #[must_use]
    pub fn overlaps(&self, other: &TimeRange) -> bool {
        self.start < other.end && other.start < self.end
    }

    /// Checks if this range is adjacent to another range.
    ///
    /// Two ranges are adjacent if one ends exactly where the other begins,
    /// with no gap and no overlap between them.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(10), Position::from_frames(20)).unwrap();
    /// let c = TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap();
    ///
    /// assert!(a.adjacent(&b));  // a ends at 10, b starts at 10
    /// assert!(b.adjacent(&a));  // Symmetric
    /// assert!(!a.adjacent(&c)); // Overlapping, not adjacent
    /// ```
    #[must_use]
    pub fn adjacent(&self, other: &TimeRange) -> bool {
        self.end == other.start || other.end == self.start
    }

    /// Returns the overlap region between this range and another, if any.
    ///
    /// Returns `None` if the ranges do not overlap.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap();
    ///
    /// let overlap = a.overlap(&b).unwrap();
    /// assert_eq!(overlap.start().frames(), 5);
    /// assert_eq!(overlap.end().frames(), 10);
    /// ```
    #[must_use]
    pub fn overlap(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) {
            return None;
        }
        let start = std::cmp::max(self.start, other.start);
        let end = std::cmp::min(self.end, other.end);
        Some(TimeRange { start, end })
    }

    /// Returns the gap between this range and another, if any.
    ///
    /// Returns `None` if the ranges overlap or are adjacent.
    /// Works correctly regardless of the order of the ranges.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(20), Position::from_frames(30)).unwrap();
    ///
    /// let gap = a.gap(&b).unwrap();
    /// assert_eq!(gap.start().frames(), 10);
    /// assert_eq!(gap.end().frames(), 20);
    ///
    /// // Works in either order
    /// assert_eq!(b.gap(&a), a.gap(&b));
    /// ```
    #[must_use]
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

    /// Returns the intersection of this range and another.
    ///
    /// This is an alias for [`overlap`](Self::overlap).
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap();
    ///
    /// let intersection = a.intersection(&b).unwrap();
    /// assert_eq!(intersection.start().frames(), 5);
    /// assert_eq!(intersection.end().frames(), 10);
    /// ```
    #[must_use]
    pub fn intersection(&self, other: &TimeRange) -> Option<TimeRange> {
        self.overlap(other)
    }

    /// Returns the union of this range and another, if they are contiguous.
    ///
    /// Two ranges are contiguous if they overlap or are adjacent.
    /// Returns `None` if the ranges are disjoint (have a gap between them).
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(10), Position::from_frames(20)).unwrap();
    ///
    /// let union = a.union(&b).unwrap();
    /// assert_eq!(union.start().frames(), 0);
    /// assert_eq!(union.end().frames(), 20);
    ///
    /// // Disjoint ranges cannot be unioned
    /// let c = TimeRange::new(Position::from_frames(30), Position::from_frames(40)).unwrap();
    /// assert!(a.union(&c).is_none());
    /// ```
    #[must_use]
    pub fn union(&self, other: &TimeRange) -> Option<TimeRange> {
        if !self.overlaps(other) && !self.adjacent(other) {
            return None;
        }
        Some(TimeRange {
            start: std::cmp::min(self.start, other.start),
            end: std::cmp::max(self.end, other.end),
        })
    }

    /// Returns the difference of this range minus another.
    ///
    /// The result may contain 0, 1, or 2 ranges:
    /// - 0 ranges if this range is completely contained in the other
    /// - 1 range if the other range clips one end of this range
    /// - 2 ranges if the other range cuts a hole in the middle of this range
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{TimeRange, Position};
    ///
    /// let a = TimeRange::new(Position::from_frames(0), Position::from_frames(30)).unwrap();
    /// let b = TimeRange::new(Position::from_frames(10), Position::from_frames(20)).unwrap();
    ///
    /// // b cuts a hole in a, resulting in two ranges
    /// let diff = a.difference(&b);
    /// assert_eq!(diff.len(), 2);
    /// assert_eq!(diff[0].start().frames(), 0);
    /// assert_eq!(diff[0].end().frames(), 10);
    /// assert_eq!(diff[1].start().frames(), 20);
    /// assert_eq!(diff[1].end().frames(), 30);
    /// ```
    #[must_use]
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

#[pymethods]
impl TimeRange {
    /// Creates a new time range from start and end positions.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position (inclusive)
    /// * `end` - The end position (exclusive)
    ///
    /// # Raises
    ///
    /// ValueError: If end <= start
    #[new]
    fn py_new(start: Position, end: Position) -> PyResult<Self> {
        Self::new(start, end)
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("end must be greater than start"))
    }

    /// Returns the start position of the range.
    #[getter]
    #[pyo3(name = "start")]
    fn py_start(&self) -> Position {
        self.start()
    }

    /// Returns the end position of the range.
    #[getter]
    #[pyo3(name = "end")]
    fn py_end(&self) -> Position {
        self.end()
    }

    /// Returns the duration of the range.
    #[getter]
    #[pyo3(name = "duration")]
    fn py_duration(&self) -> Duration {
        self.duration()
    }

    /// Checks if this range overlaps with another range.
    #[pyo3(name = "overlaps")]
    fn py_overlaps(&self, other: &TimeRange) -> bool {
        self.overlaps(other)
    }

    /// Checks if this range is adjacent to another range.
    #[pyo3(name = "adjacent")]
    fn py_adjacent(&self, other: &TimeRange) -> bool {
        self.adjacent(other)
    }

    /// Returns the overlap region between this range and another, if any.
    #[pyo3(name = "overlap")]
    fn py_overlap(&self, other: &TimeRange) -> Option<TimeRange> {
        self.overlap(other)
    }

    /// Returns the gap between this range and another, if any.
    #[pyo3(name = "gap")]
    fn py_gap(&self, other: &TimeRange) -> Option<TimeRange> {
        self.gap(other)
    }

    /// Returns the intersection of this range and another.
    #[pyo3(name = "intersection")]
    fn py_intersection(&self, other: &TimeRange) -> Option<TimeRange> {
        self.intersection(other)
    }

    /// Returns the union of this range and another, if they are contiguous.
    #[pyo3(name = "union")]
    fn py_union(&self, other: &TimeRange) -> Option<TimeRange> {
        self.union(other)
    }

    /// Returns the difference of this range minus another.
    #[pyo3(name = "difference")]
    fn py_difference(&self, other: &TimeRange) -> Vec<TimeRange> {
        self.difference(other)
    }

    /// Returns a string representation of the time range.
    fn __repr__(&self) -> String {
        format!(
            "TimeRange(start={}, end={})",
            self.start.frames(),
            self.end.frames()
        )
    }

    /// Compares two time ranges for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.start == other.start && self.end == other.end
    }
}

/// Finds gaps between non-overlapping portions of the given ranges.
///
/// The ranges are sorted by start position and merged, then gaps
/// between merged ranges are returned.
///
/// Time complexity: O(n log n) due to sorting.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{find_gaps, TimeRange, Position};
///
/// let ranges = vec![
///     TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap(),
///     TimeRange::new(Position::from_frames(20), Position::from_frames(30)).unwrap(),
/// ];
///
/// let gaps = find_gaps(&ranges);
/// assert_eq!(gaps.len(), 1);
/// assert_eq!(gaps[0].start().frames(), 10);
/// assert_eq!(gaps[0].end().frames(), 20);
/// ```
#[must_use]
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

/// Merges overlapping and adjacent ranges into non-overlapping ranges.
///
/// The result is a minimal set of non-overlapping, non-adjacent ranges
/// that cover the same time as the input ranges.
///
/// Time complexity: O(n log n) due to sorting.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{merge_ranges, TimeRange, Position};
///
/// let ranges = vec![
///     TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap(),
///     TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap(),
///     TimeRange::new(Position::from_frames(20), Position::from_frames(30)).unwrap(),
/// ];
///
/// let merged = merge_ranges(&ranges);
/// assert_eq!(merged.len(), 2);
/// assert_eq!(merged[0].start().frames(), 0);
/// assert_eq!(merged[0].end().frames(), 15);
/// assert_eq!(merged[1].start().frames(), 20);
/// assert_eq!(merged[1].end().frames(), 30);
/// ```
#[must_use]
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

/// Calculates the total duration covered by the given ranges.
///
/// Overlapping ranges are merged before calculating the total,
/// so overlapping portions are only counted once.
///
/// Time complexity: O(n log n) due to sorting during merge.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{total_coverage, TimeRange, Position};
///
/// let ranges = vec![
///     TimeRange::new(Position::from_frames(0), Position::from_frames(10)).unwrap(),
///     TimeRange::new(Position::from_frames(5), Position::from_frames(15)).unwrap(),  // Overlaps
///     TimeRange::new(Position::from_frames(20), Position::from_frames(30)).unwrap(),
/// ];
///
/// let total = total_coverage(&ranges);
/// assert_eq!(total.frames(), 25);  // 15 + 10, not 10 + 10 + 10
/// ```
#[must_use]
pub fn total_coverage(ranges: &[TimeRange]) -> Duration {
    let merged = merge_ranges(ranges);
    let total_frames: u64 = merged.iter().map(|r| r.duration().frames()).sum();
    Duration::from_frames(total_frames)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Helper to create a TimeRange from frame numbers
    fn range(start: u64, end: u64) -> TimeRange {
        TimeRange::new(Position::from_frames(start), Position::from_frames(end)).unwrap()
    }

    #[test]
    fn test_new_valid() {
        let r = TimeRange::new(Position::from_frames(0), Position::from_frames(10));
        assert!(r.is_ok());
        let r = r.unwrap();
        assert_eq!(r.start().frames(), 0);
        assert_eq!(r.end().frames(), 10);
    }

    #[test]
    fn test_new_invalid_same() {
        let r = TimeRange::new(Position::from_frames(10), Position::from_frames(10));
        assert!(matches!(r, Err(RangeError::InvalidBounds)));
    }

    #[test]
    fn test_new_invalid_reversed() {
        let r = TimeRange::new(Position::from_frames(20), Position::from_frames(10));
        assert!(matches!(r, Err(RangeError::InvalidBounds)));
    }

    #[test]
    fn test_duration() {
        let r = range(10, 30);
        assert_eq!(r.duration().frames(), 20);
    }

    #[test]
    fn test_overlaps_true() {
        let a = range(0, 10);
        let b = range(5, 15);
        assert!(a.overlaps(&b));
        assert!(b.overlaps(&a));
    }

    #[test]
    fn test_overlaps_false_adjacent() {
        let a = range(0, 10);
        let b = range(10, 20);
        assert!(!a.overlaps(&b));
        assert!(!b.overlaps(&a));
    }

    #[test]
    fn test_overlaps_false_disjoint() {
        let a = range(0, 10);
        let b = range(20, 30);
        assert!(!a.overlaps(&b));
        assert!(!b.overlaps(&a));
    }

    #[test]
    fn test_overlaps_contained() {
        let a = range(0, 30);
        let b = range(10, 20);
        assert!(a.overlaps(&b));
        assert!(b.overlaps(&a));
    }

    #[test]
    fn test_adjacent() {
        let a = range(0, 10);
        let b = range(10, 20);
        assert!(a.adjacent(&b));
        assert!(b.adjacent(&a));
    }

    #[test]
    fn test_not_adjacent_overlapping() {
        let a = range(0, 15);
        let b = range(10, 20);
        assert!(!a.adjacent(&b));
    }

    #[test]
    fn test_not_adjacent_disjoint() {
        let a = range(0, 10);
        let b = range(20, 30);
        assert!(!a.adjacent(&b));
    }

    #[test]
    fn test_overlap_result() {
        let a = range(0, 10);
        let b = range(5, 15);
        let overlap = a.overlap(&b).unwrap();
        assert_eq!(overlap.start().frames(), 5);
        assert_eq!(overlap.end().frames(), 10);
    }

    #[test]
    fn test_overlap_none() {
        let a = range(0, 10);
        let b = range(10, 20);
        assert!(a.overlap(&b).is_none());
    }

    #[test]
    fn test_gap() {
        let a = range(0, 10);
        let b = range(20, 30);
        let gap = a.gap(&b).unwrap();
        assert_eq!(gap.start().frames(), 10);
        assert_eq!(gap.end().frames(), 20);
    }

    #[test]
    fn test_gap_symmetric() {
        let a = range(0, 10);
        let b = range(20, 30);
        assert_eq!(a.gap(&b), b.gap(&a));
    }

    #[test]
    fn test_gap_none_overlapping() {
        let a = range(0, 15);
        let b = range(10, 20);
        assert!(a.gap(&b).is_none());
    }

    #[test]
    fn test_gap_none_adjacent() {
        let a = range(0, 10);
        let b = range(10, 20);
        assert!(a.gap(&b).is_none());
    }

    #[test]
    fn test_intersection() {
        let a = range(0, 10);
        let b = range(5, 15);
        let intersection = a.intersection(&b).unwrap();
        assert_eq!(intersection.start().frames(), 5);
        assert_eq!(intersection.end().frames(), 10);
    }

    #[test]
    fn test_union_overlapping() {
        let a = range(0, 10);
        let b = range(5, 15);
        let union = a.union(&b).unwrap();
        assert_eq!(union.start().frames(), 0);
        assert_eq!(union.end().frames(), 15);
    }

    #[test]
    fn test_union_adjacent() {
        let a = range(0, 10);
        let b = range(10, 20);
        let union = a.union(&b).unwrap();
        assert_eq!(union.start().frames(), 0);
        assert_eq!(union.end().frames(), 20);
    }

    #[test]
    fn test_union_none_disjoint() {
        let a = range(0, 10);
        let b = range(20, 30);
        assert!(a.union(&b).is_none());
    }

    #[test]
    fn test_difference_no_overlap() {
        let a = range(0, 10);
        let b = range(20, 30);
        let diff = a.difference(&b);
        assert_eq!(diff.len(), 1);
        assert_eq!(diff[0], a);
    }

    #[test]
    fn test_difference_clips_end() {
        let a = range(0, 20);
        let b = range(15, 30);
        let diff = a.difference(&b);
        assert_eq!(diff.len(), 1);
        assert_eq!(diff[0].start().frames(), 0);
        assert_eq!(diff[0].end().frames(), 15);
    }

    #[test]
    fn test_difference_clips_start() {
        let a = range(10, 30);
        let b = range(0, 15);
        let diff = a.difference(&b);
        assert_eq!(diff.len(), 1);
        assert_eq!(diff[0].start().frames(), 15);
        assert_eq!(diff[0].end().frames(), 30);
    }

    #[test]
    fn test_difference_cuts_hole() {
        let a = range(0, 30);
        let b = range(10, 20);
        let diff = a.difference(&b);
        assert_eq!(diff.len(), 2);
        assert_eq!(diff[0].start().frames(), 0);
        assert_eq!(diff[0].end().frames(), 10);
        assert_eq!(diff[1].start().frames(), 20);
        assert_eq!(diff[1].end().frames(), 30);
    }

    #[test]
    fn test_difference_completely_contained() {
        let a = range(10, 20);
        let b = range(0, 30);
        let diff = a.difference(&b);
        assert_eq!(diff.len(), 0);
    }

    #[test]
    fn test_find_gaps_empty() {
        let gaps = find_gaps(&[]);
        assert!(gaps.is_empty());
    }

    #[test]
    fn test_find_gaps_single() {
        let gaps = find_gaps(&[range(0, 10)]);
        assert!(gaps.is_empty());
    }

    #[test]
    fn test_find_gaps_with_gap() {
        let ranges = vec![range(0, 10), range(20, 30)];
        let gaps = find_gaps(&ranges);
        assert_eq!(gaps.len(), 1);
        assert_eq!(gaps[0].start().frames(), 10);
        assert_eq!(gaps[0].end().frames(), 20);
    }

    #[test]
    fn test_find_gaps_overlapping() {
        let ranges = vec![range(0, 15), range(10, 20)];
        let gaps = find_gaps(&ranges);
        assert!(gaps.is_empty());
    }

    #[test]
    fn test_find_gaps_unsorted() {
        let ranges = vec![range(20, 30), range(0, 10)];
        let gaps = find_gaps(&ranges);
        assert_eq!(gaps.len(), 1);
        assert_eq!(gaps[0].start().frames(), 10);
        assert_eq!(gaps[0].end().frames(), 20);
    }

    #[test]
    fn test_merge_ranges_empty() {
        let merged = merge_ranges(&[]);
        assert!(merged.is_empty());
    }

    #[test]
    fn test_merge_ranges_single() {
        let merged = merge_ranges(&[range(0, 10)]);
        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0], range(0, 10));
    }

    #[test]
    fn test_merge_ranges_overlapping() {
        let ranges = vec![range(0, 10), range(5, 15)];
        let merged = merge_ranges(&ranges);
        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0].start().frames(), 0);
        assert_eq!(merged[0].end().frames(), 15);
    }

    #[test]
    fn test_merge_ranges_adjacent() {
        let ranges = vec![range(0, 10), range(10, 20)];
        let merged = merge_ranges(&ranges);
        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0].start().frames(), 0);
        assert_eq!(merged[0].end().frames(), 20);
    }

    #[test]
    fn test_merge_ranges_disjoint() {
        let ranges = vec![range(0, 10), range(20, 30)];
        let merged = merge_ranges(&ranges);
        assert_eq!(merged.len(), 2);
    }

    #[test]
    fn test_merge_ranges_unsorted() {
        let ranges = vec![range(20, 30), range(0, 10), range(5, 15)];
        let merged = merge_ranges(&ranges);
        assert_eq!(merged.len(), 2);
        assert_eq!(merged[0].start().frames(), 0);
        assert_eq!(merged[0].end().frames(), 15);
        assert_eq!(merged[1].start().frames(), 20);
        assert_eq!(merged[1].end().frames(), 30);
    }

    #[test]
    fn test_total_coverage_empty() {
        let total = total_coverage(&[]);
        assert_eq!(total.frames(), 0);
    }

    #[test]
    fn test_total_coverage_single() {
        let total = total_coverage(&[range(0, 10)]);
        assert_eq!(total.frames(), 10);
    }

    #[test]
    fn test_total_coverage_overlapping() {
        let ranges = vec![range(0, 10), range(5, 15), range(20, 30)];
        let total = total_coverage(&ranges);
        assert_eq!(total.frames(), 25); // 15 + 10
    }

    #[test]
    fn test_total_coverage_no_double_count() {
        let ranges = vec![range(0, 10), range(0, 10)]; // Same range twice
        let total = total_coverage(&ranges);
        assert_eq!(total.frames(), 10);
    }

    #[test]
    fn test_range_error_display() {
        let err = RangeError::InvalidBounds;
        assert_eq!(
            format!("{}", err),
            "invalid bounds: end must be greater than start"
        );
    }

    // Property tests
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

        #[test]
        fn adjacent_is_symmetric(
            s1 in 0u64..1000, e1 in 1u64..1001,
            s2 in 0u64..1000, e2 in 1u64..1001,
        ) {
            prop_assume!(e1 > s1 && e2 > s2);
            let a = TimeRange::new(Position::from_frames(s1), Position::from_frames(e1)).unwrap();
            let b = TimeRange::new(Position::from_frames(s2), Position::from_frames(e2)).unwrap();
            prop_assert_eq!(a.adjacent(&b), b.adjacent(&a));
        }

        #[test]
        fn gap_is_symmetric(
            s1 in 0u64..1000, e1 in 1u64..1001,
            s2 in 0u64..1000, e2 in 1u64..1001,
        ) {
            prop_assume!(e1 > s1 && e2 > s2);
            let a = TimeRange::new(Position::from_frames(s1), Position::from_frames(e1)).unwrap();
            let b = TimeRange::new(Position::from_frames(s2), Position::from_frames(e2)).unwrap();
            prop_assert_eq!(a.gap(&b), b.gap(&a));
        }

        #[test]
        fn intersection_is_symmetric(
            s1 in 0u64..1000, e1 in 1u64..1001,
            s2 in 0u64..1000, e2 in 1u64..1001,
        ) {
            prop_assume!(e1 > s1 && e2 > s2);
            let a = TimeRange::new(Position::from_frames(s1), Position::from_frames(e1)).unwrap();
            let b = TimeRange::new(Position::from_frames(s2), Position::from_frames(e2)).unwrap();
            prop_assert_eq!(a.intersection(&b), b.intersection(&a));
        }

        #[test]
        fn union_is_symmetric(
            s1 in 0u64..1000, e1 in 1u64..1001,
            s2 in 0u64..1000, e2 in 1u64..1001,
        ) {
            prop_assume!(e1 > s1 && e2 > s2);
            let a = TimeRange::new(Position::from_frames(s1), Position::from_frames(e1)).unwrap();
            let b = TimeRange::new(Position::from_frames(s2), Position::from_frames(e2)).unwrap();
            prop_assert_eq!(a.union(&b), b.union(&a));
        }

        #[test]
        fn merged_ranges_cover_same_total(ranges in prop::collection::vec((0u64..1000, 1u64..1001), 1..10)) {
            let valid_ranges: Vec<TimeRange> = ranges
                .iter()
                .filter(|(s, e)| e > s)
                .map(|(s, e)| TimeRange::new(Position::from_frames(*s), Position::from_frames(*e)).unwrap())
                .collect();

            if !valid_ranges.is_empty() {
                let merged = merge_ranges(&valid_ranges);
                let total_before = total_coverage(&valid_ranges);
                let total_after = total_coverage(&merged);
                prop_assert_eq!(total_before, total_after);
            }
        }

        #[test]
        fn merged_ranges_have_no_overlap(ranges in prop::collection::vec((0u64..1000, 1u64..1001), 1..10)) {
            let valid_ranges: Vec<TimeRange> = ranges
                .iter()
                .filter(|(s, e)| e > s)
                .map(|(s, e)| TimeRange::new(Position::from_frames(*s), Position::from_frames(*e)).unwrap())
                .collect();

            if !valid_ranges.is_empty() {
                let merged = merge_ranges(&valid_ranges);
                for i in 0..merged.len() {
                    for j in (i + 1)..merged.len() {
                        prop_assert!(!merged[i].overlaps(&merged[j]));
                    }
                }
            }
        }

        #[test]
        fn duration_equals_end_minus_start(s in 0u64..1_000_000, len in 1u64..1_000_000) {
            let r = TimeRange::new(
                Position::from_frames(s),
                Position::from_frames(s + len),
            ).unwrap();
            prop_assert_eq!(r.duration().frames(), len);
        }
    }
}
