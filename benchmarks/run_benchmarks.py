"""Main benchmark runner comparing Rust (PyO3) vs pure Python implementations.

Run with: uv run python -m benchmarks
Or:       uv run python benchmarks/run_benchmarks.py
"""

from __future__ import annotations

import platform
import sys

from benchmarks.bench_filter_escape import run_all as run_filter_escape
from benchmarks.bench_timeline import run_all as run_timeline
from benchmarks.bench_validation import run_all as run_validation
from benchmarks.timing import BenchmarkResult, print_result


def print_summary_table(results: list[BenchmarkResult]) -> None:
    """Print a summary table of all benchmark results.

    Args:
        results: List of BenchmarkResult objects to summarize.
    """
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    header = f"  {'Benchmark':<45s} {'Speedup (mean)':>12s} {'Winner':>8s}"
    print(header)
    print(f"  {'-' * 66}")
    for r in results:
        winner = "Rust" if r.speedup_mean > 1 else "Python"
        ratio = f"{r.speedup_mean:.2f}x" if r.speedup_mean > 1 else f"{1 / r.speedup_mean:.2f}x"
        label = f"{ratio} ({winner})"
        print(f"  {r.name:<45s} {label:>20s}")
    print(f"{'=' * 70}")


def print_environment() -> None:
    """Print system environment information for reproducibility."""
    print(f"\n{'=' * 70}")
    print("  ENVIRONMENT")
    print(f"{'=' * 70}")
    print(f"  Python:   {sys.version}")
    print(f"  Platform: {platform.platform()}")
    print(f"  CPU:      {platform.processor() or 'unknown'}")

    try:
        from stoat_ferret_core import health_check

        print(f"  Rust:     {health_check()}")
    except ImportError:
        print("  Rust:     NOT AVAILABLE")
    print(f"{'=' * 70}")


def main() -> None:
    """Run all benchmarks and print results."""
    print_environment()

    print("\n  Running benchmarks... (this may take a minute)\n")

    all_results: list[BenchmarkResult] = []

    # Timeline arithmetic
    print("  [1/3] Timeline position arithmetic...")
    all_results.extend(run_timeline())

    # Filter text escaping
    print("  [2/3] Filter text escaping...")
    all_results.extend(run_filter_escape())

    # Path validation
    print("  [3/3] Path validation...")
    all_results.extend(run_validation())

    # Print individual results
    for result in all_results:
        print_result(result)

    # Print summary
    print_summary_table(all_results)


if __name__ == "__main__":
    main()
