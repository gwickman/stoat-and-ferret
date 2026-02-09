"""Benchmarks for TimeRange list operations: Rust vs Python.

Compares merge_ranges and find_gaps (Rust via PyO3) against pure Python
equivalents that perform the same sorting and merging algorithms.
"""

from __future__ import annotations

import random

from benchmarks.timing import BenchmarkResult, run_benchmark
from stoat_ferret_core import Position, TimeRange, find_gaps, merge_ranges

# --- Pure Python reference implementations ---


def py_merge_ranges(
    ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Merge overlapping and adjacent ranges using pure Python.

    Mirrors the Rust merge_ranges logic: sort by start, then iterate
    and union overlapping/adjacent ranges.

    Args:
        ranges: List of (start_frame, end_frame) tuples.

    Returns:
        List of merged (start_frame, end_frame) tuples.
    """
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda r: r[0])
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:  # overlapping or adjacent
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def py_find_gaps(
    ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Find gaps between merged ranges using pure Python.

    Mirrors the Rust find_gaps logic: merge ranges first, then
    find gaps between consecutive merged ranges.

    Args:
        ranges: List of (start_frame, end_frame) tuples.

    Returns:
        List of (start_frame, end_frame) tuples representing gaps.
    """
    merged = py_merge_ranges(ranges)
    if len(merged) < 2:
        return []
    gaps: list[tuple[int, int]] = []
    for i in range(len(merged) - 1):
        gap_start = merged[i][1]
        gap_end = merged[i + 1][0]
        if gap_end > gap_start:
            gaps.append((gap_start, gap_end))
    return gaps


# --- Test data generation ---


def _make_rust_ranges(raw: list[tuple[int, int]]) -> list[TimeRange]:
    """Convert raw (start, end) tuples to Rust TimeRange objects.

    Args:
        raw: List of (start_frame, end_frame) tuples.

    Returns:
        List of TimeRange objects.
    """
    result: list[TimeRange] = []
    for start, end in raw:
        result.append(TimeRange(Position(start), Position(end)))
    return result


def _generate_ranges(count: int, seed: int = 42) -> list[tuple[int, int]]:
    """Generate random ranges for benchmarking.

    Args:
        count: Number of ranges to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of (start_frame, end_frame) tuples.
    """
    rng = random.Random(seed)
    ranges: list[tuple[int, int]] = []
    for _ in range(count):
        start = rng.randint(0, 100000)
        length = rng.randint(10, 500)
        ranges.append((start, start + length))
    return ranges


# Pre-generate test data (done once at import time for consistent benchmarks)
_RANGES_100 = _generate_ranges(100)
_RANGES_500 = _generate_ranges(500)

# Pre-convert to Rust types
_RUST_RANGES_100 = _make_rust_ranges(_RANGES_100)
_RUST_RANGES_500 = _make_rust_ranges(_RANGES_500)


# --- Benchmark definitions ---


def run_merge_ranges_benchmark() -> BenchmarkResult:
    """Benchmark merge_ranges: Rust vs Python.

    Tests merging 100 random overlapping ranges.

    Returns:
        BenchmarkResult with timing data.
    """

    def rust_impl() -> None:
        merge_ranges(_RUST_RANGES_100)

    def python_impl() -> None:
        py_merge_ranges(_RANGES_100)

    return run_benchmark(
        name="merge_ranges (100 ranges, sort + merge)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=500,
    )


def run_merge_ranges_large_benchmark() -> BenchmarkResult:
    """Benchmark merge_ranges with larger input: Rust vs Python.

    Tests merging 500 random overlapping ranges.

    Returns:
        BenchmarkResult with timing data.
    """

    def rust_impl() -> None:
        merge_ranges(_RUST_RANGES_500)

    def python_impl() -> None:
        py_merge_ranges(_RANGES_500)

    return run_benchmark(
        name="merge_ranges (500 ranges, sort + merge)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=200,
    )


def run_find_gaps_benchmark() -> BenchmarkResult:
    """Benchmark find_gaps: Rust vs Python.

    Tests gap detection on 100 random ranges.

    Returns:
        BenchmarkResult with timing data.
    """

    def rust_impl() -> None:
        find_gaps(_RUST_RANGES_100)

    def python_impl() -> None:
        py_find_gaps(_RANGES_100)

    return run_benchmark(
        name="find_gaps (100 ranges, sort + gap detection)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=500,
    )


def run_all() -> list[BenchmarkResult]:
    """Run all range operation benchmarks.

    Returns:
        List of BenchmarkResult objects.
    """
    return [
        run_merge_ranges_benchmark(),
        run_merge_ranges_large_benchmark(),
        run_find_gaps_benchmark(),
    ]
