"""Benchmarks for FFmpeg filter text escaping: Rust vs Python.

Compares escape_filter_text (Rust via PyO3) against a pure Python
equivalent that escapes the same special characters.
"""

from __future__ import annotations

from benchmarks.timing import BenchmarkResult, run_benchmark
from stoat_ferret_core import escape_filter_text

# --- Pure Python reference implementation ---

# Mapping of special chars to their escaped forms
_ESCAPE_MAP: dict[str, str] = {
    "\\": "\\\\",
    "'": "'\\''",
    ":": "\\:",
    "[": "\\[",
    "]": "\\]",
    ";": "\\;",
    "\n": "\\n",
    "\r": "\\r",
}


def py_escape_filter_text(text: str) -> str:
    """Escape special FFmpeg filter characters using pure Python.

    Mirrors the Rust escape_filter_text logic: iterates through each
    character and replaces special chars with their escaped forms.

    Args:
        text: The input text to escape.

    Returns:
        Escaped text safe for FFmpeg filter parameters.
    """
    result: list[str] = []
    for char in text:
        result.append(_ESCAPE_MAP.get(char, char))
    return "".join(result)


# --- Test inputs with varying special character density ---

_INPUTS: list[str] = [
    # No special chars
    "hello world this is normal text without any special characters at all",
    # Low density (~10% special)
    "input file: video.mp4; output: result.mp4",
    # Medium density (~25% special)
    "text: [label]; path\\to\\file; key:value; name's",
    # High density (~50% special)
    "\\':[];\\':[];\\':[];\\':[];\\':[];",
    # UTF-8 with special chars
    "日本語: テスト; emoji: 🎬; path\\ファイル",
    # Long string (500 chars, ~10% special)
    ("The quick brown fox: jumps; over [the] lazy dog. " * 10),
]


# --- Benchmark definitions ---


def run_escape_benchmark() -> BenchmarkResult:
    """Benchmark escape_filter_text: Rust vs Python.

    Tests escaping across strings with varying lengths and
    special character densities.

    Returns:
        BenchmarkResult with timing data.
    """

    def rust_impl() -> None:
        for text in _INPUTS:
            escape_filter_text(text)

    def python_impl() -> None:
        for text in _INPUTS:
            py_escape_filter_text(text)

    return run_benchmark(
        name="escape_filter_text (string escaping)",
        rust_func=rust_impl,
        python_func=python_impl,
        iterations=1000,
    )


def run_all() -> list[BenchmarkResult]:
    """Run all filter escape benchmarks.

    Returns:
        List of BenchmarkResult objects.
    """
    return [run_escape_benchmark()]
