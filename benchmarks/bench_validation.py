"""Benchmarks for path validation: Rust vs Python.

Compares validate_path (Rust via PyO3) against a pure Python
equivalent that performs the same checks.
"""

from __future__ import annotations

from benchmarks.timing import BenchmarkResult, run_benchmark
from stoat_ferret_core import validate_path

# --- Pure Python reference implementation ---


def py_validate_path(path: str) -> None:
    """Validate a file path using pure Python.

    Mirrors the Rust validate_path logic:
    - Rejects empty paths
    - Rejects paths containing null bytes

    Args:
        path: The path to validate.

    Raises:
        ValueError: If the path is empty or contains null bytes.
    """
    if not path:
        raise ValueError("Path cannot be empty")
    if "\0" in path:
        raise ValueError("Path cannot contain null bytes")


# --- Test inputs ---

_VALID_PATHS: list[str] = [
    "input.mp4",
    "/path/to/file.mp4",
    "C:\\Users\\video\\project\\output.mp4",
    "file with spaces and unicode 日本語.mp4",
    "../relative/path/to/media/file.mkv",
    "/very/long/path/" + "subdir/" * 50 + "file.mp4",
    "simple.txt",
    "/a/b/c/d/e/f/g/h/i/j.mp4",
]


# --- Benchmark definitions ---


def run_validate_path_benchmark() -> BenchmarkResult:
    """Benchmark validate_path: Rust vs Python.

    Tests path validation across various valid paths.
    We only test valid paths since both implementations raise
    on invalid input, and exception handling would dominate timing.

    Returns:
        BenchmarkResult with timing data.
    """

    def rust_impl() -> None:
        for path in _VALID_PATHS:
            validate_path(path)

    def python_impl() -> None:
        for path in _VALID_PATHS:
            py_validate_path(path)

    return run_benchmark(
        name="validate_path (path safety check)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=1000,
    )


def run_all() -> list[BenchmarkResult]:
    """Run all validation benchmarks.

    Returns:
        List of BenchmarkResult objects.
    """
    return [run_validate_path_benchmark()]
