"""Benchmarks for timeline position arithmetic: Rust vs Python.

Compares Position.from_secs (Rust via PyO3) against a pure Python
equivalent performing the same frame calculation.
"""

from __future__ import annotations

from benchmarks.timing import BenchmarkResult, run_benchmark
from stoat_ferret_core import FrameRate, Position

# --- Pure Python reference implementation ---


def py_from_seconds(seconds: float, numerator: int, denominator: int) -> int:
    """Convert seconds to frame count using pure Python arithmetic.

    Mirrors the Rust Position::from_seconds logic:
        frames = round(seconds * numerator / denominator)

    Args:
        seconds: Time in seconds.
        numerator: Frame rate numerator.
        denominator: Frame rate denominator.

    Returns:
        Frame count as integer.
    """
    return round(seconds * numerator / denominator)


def py_to_seconds(frames: int, numerator: int, denominator: int) -> float:
    """Convert frame count to seconds using pure Python arithmetic.

    Mirrors the Rust Position::to_seconds logic:
        seconds = frames * denominator / numerator

    Args:
        frames: Frame count.
        numerator: Frame rate numerator.
        denominator: Frame rate denominator.

    Returns:
        Time in seconds.
    """
    return frames * denominator / numerator


# --- Benchmark definitions ---


def run_from_seconds_benchmark() -> BenchmarkResult:
    """Benchmark Position.from_seconds: Rust vs Python.

    Tests conversion of seconds to frame counts across multiple
    frame rates and time values.

    Returns:
        BenchmarkResult with timing data.
    """
    fps_24 = FrameRate(24, 1)
    fps_ntsc = FrameRate(30000, 1001)
    fps_60 = FrameRate(60, 1)
    test_values = [0.0, 0.5, 1.0, 2.5, 10.0, 60.0, 3600.0]

    def rust_impl() -> None:
        for sec in test_values:
            Position.from_secs(sec, fps_24)
            Position.from_secs(sec, fps_ntsc)
            Position.from_secs(sec, fps_60)

    def python_impl() -> None:
        for sec in test_values:
            py_from_seconds(sec, 24, 1)
            py_from_seconds(sec, 30000, 1001)
            py_from_seconds(sec, 60, 1)

    return run_benchmark(
        name="Position.from_seconds (seconds -> frames)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=1000,
    )


def run_to_seconds_benchmark() -> BenchmarkResult:
    """Benchmark Position.to_seconds: Rust vs Python.

    Tests conversion of frame counts to seconds.

    Returns:
        BenchmarkResult with timing data.
    """
    fps_24 = FrameRate(24, 1)
    fps_ntsc = FrameRate(30000, 1001)
    test_frames = [0, 24, 100, 720, 1800, 86400]
    positions = [Position(f) for f in test_frames]

    def rust_impl() -> None:
        for pos in positions:
            pos.as_secs(fps_24)
            pos.as_secs(fps_ntsc)

    def python_impl() -> None:
        for f in test_frames:
            py_to_seconds(f, 24, 1)
            py_to_seconds(f, 30000, 1001)

    return run_benchmark(
        name="Position.to_seconds (frames -> seconds)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=1000,
    )


def run_all() -> list[BenchmarkResult]:
    """Run all timeline benchmarks.

    Returns:
        List of BenchmarkResult objects.
    """
    return [
        run_from_seconds_benchmark(),
        run_to_seconds_benchmark(),
    ]
