"""Benchmark timing utilities with warmup, multiple iterations, and statistics."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Result of a single benchmark comparison between Rust and Python."""

    name: str
    rust_times: list[float]
    python_times: list[float]
    iterations: int

    @property
    def rust_mean(self) -> float:
        """Mean execution time for Rust in seconds."""
        return statistics.mean(self.rust_times)

    @property
    def python_mean(self) -> float:
        """Mean execution time for Python in seconds."""
        return statistics.mean(self.python_times)

    @property
    def rust_median(self) -> float:
        """Median execution time for Rust in seconds."""
        return statistics.median(self.rust_times)

    @property
    def python_median(self) -> float:
        """Median execution time for Python in seconds."""
        return statistics.median(self.python_times)

    @property
    def rust_stdev(self) -> float:
        """Standard deviation for Rust times."""
        if len(self.rust_times) < 2:
            return 0.0
        return statistics.stdev(self.rust_times)

    @property
    def python_stdev(self) -> float:
        """Standard deviation for Python times."""
        if len(self.python_times) < 2:
            return 0.0
        return statistics.stdev(self.python_times)

    @property
    def speedup_mean(self) -> float:
        """Speedup ratio (Python mean / Rust mean). >1 means Rust is faster."""
        if self.rust_mean == 0:
            return float("inf")
        return self.python_mean / self.rust_mean

    @property
    def speedup_median(self) -> float:
        """Speedup ratio (Python median / Rust median). >1 means Rust is faster."""
        if self.rust_median == 0:
            return float("inf")
        return self.python_median / self.rust_median


def time_function(func: object, iterations: int) -> list[float]:
    """Time a function over multiple runs, returning per-run times in seconds.

    Each run executes the function `iterations` times and records the total
    time for that batch. Returns a list of batch times.

    Args:
        func: Callable to benchmark (takes no arguments).
        iterations: Number of times to call func per run.

    Returns:
        List of elapsed times (one per run).
    """
    times: list[float] = []
    for _ in range(10):  # 10 runs
        start = time.perf_counter()
        for _ in range(iterations):
            func()  # type: ignore[operator]
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def run_benchmark(
    name: str,
    rust_func: object,
    python_func: object,
    iterations: int = 1000,
    warmup: int = 100,
) -> BenchmarkResult:
    """Run a benchmark comparing Rust vs Python implementations.

    Args:
        name: Human-readable name for the benchmark.
        rust_func: Callable wrapping the Rust implementation.
        python_func: Callable wrapping the Python implementation.
        iterations: Number of iterations per timed run.
        warmup: Number of warmup calls before timing.

    Returns:
        BenchmarkResult with timing data.
    """
    # Warmup both implementations
    for _ in range(warmup):
        rust_func()  # type: ignore[operator]
    for _ in range(warmup):
        python_func()  # type: ignore[operator]

    rust_times = time_function(rust_func, iterations)
    python_times = time_function(python_func, iterations)

    return BenchmarkResult(
        name=name,
        rust_times=rust_times,
        python_times=python_times,
        iterations=iterations,
    )


def format_time(seconds: float) -> str:
    """Format a time value with appropriate units.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted string with units (s, ms, us, ns).
    """
    if seconds >= 1.0:
        return f"{seconds:.3f}s"
    elif seconds >= 1e-3:
        return f"{seconds * 1e3:.3f}ms"
    elif seconds >= 1e-6:
        return f"{seconds * 1e6:.3f}us"
    else:
        return f"{seconds * 1e9:.3f}ns"


def print_result(result: BenchmarkResult) -> None:
    """Print a formatted benchmark result.

    Args:
        result: The benchmark result to display.
    """
    print(f"\n{'=' * 60}")
    print(f"  {result.name}")
    print(f"  ({result.iterations} iterations x 10 runs)")
    print(f"{'=' * 60}")
    print(f"  {'':20s} {'Mean':>12s} {'Median':>12s} {'StdDev':>12s}")
    print(
        f"  {'Rust (PyO3)':20s} {format_time(result.rust_mean):>12s} "
        f"{format_time(result.rust_median):>12s} "
        f"{format_time(result.rust_stdev):>12s}"
    )
    print(
        f"  {'Python':20s} {format_time(result.python_mean):>12s} "
        f"{format_time(result.python_median):>12s} "
        f"{format_time(result.python_stdev):>12s}"
    )
    print(f"  {'-' * 56}")
    print(f"  Speedup (mean):   {result.speedup_mean:.2f}x")
    print(f"  Speedup (median): {result.speedup_median:.2f}x")
    if result.speedup_mean > 1:
        print(f"  -> Rust is {result.speedup_mean:.1f}x faster")
    else:
        print(f"  -> Python is {1 / result.speedup_mean:.1f}x faster")
