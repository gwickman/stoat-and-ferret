# Performance Benchmarks: Rust vs Python

## Methodology

Each benchmark compares a Rust implementation (called via PyO3 bindings) against a
pure-Python equivalent performing the same computation. The methodology is:

- **Warmup**: 100 calls before timing to eliminate JIT/cache effects
- **Runs**: 10 timed runs per benchmark
- **Iterations**: 200-1000 iterations per run (varies by operation complexity)
- **Statistics**: Mean, median, and standard deviation reported
- **Speedup**: Calculated as `python_time / rust_time` (>1 means Rust is faster)

All benchmarks run without external dependencies (no FFmpeg, no network).

## Environment

- Python 3.13.11, Windows 11, Intel 12th Gen (Alder Lake)
- Rust module: `stoat_ferret_core` built with maturin (release mode)

## Results

### Summary Table

| Benchmark | Iterations | Rust Mean | Python Mean | Speedup | Winner |
|-----------|-----------|-----------|-------------|---------|--------|
| Position.from_secs (seconds to frames) | 1000x10 | 12.4ms | 1.7ms | 0.13x | Python (7.5x) |
| Position.as_secs (frames to seconds) | 1000x10 | 5.0ms | 0.5ms | 0.10x | Python (10.1x) |
| escape_filter_text (string escaping) | 1000x10 | 13.3ms | 25.0ms | 1.88x | **Rust (1.9x)** |
| merge_ranges (100 ranges) | 500x10 | 23.7ms | 5.0ms | 0.21x | Python (4.8x) |
| merge_ranges (500 ranges) | 200x10 | 41.7ms | 11.7ms | 0.28x | Python (3.5x) |
| find_gaps (100 ranges) | 500x10 | 23.2ms | 6.9ms | 0.30x | Python (3.4x) |
| validate_path | 1000x10 | 2.6ms | 0.3ms | 0.12x | Python (8.3x) |

### Detailed Analysis

#### 1. Timeline Position Arithmetic

**Result: Python is 7-10x faster**

`Position.from_secs` and `Position.as_secs` perform simple floating-point arithmetic
(multiply, divide, round). The pure-Python equivalent is a single expression:
`round(seconds * numerator / denominator)`. The PyO3 FFI boundary overhead
(object creation, type conversion, GIL interaction) far exceeds the computation cost.

**Verdict**: Rust offers no benefit for simple arithmetic operations. The FFI crossing
cost dominates when the actual computation is trivial.

#### 2. Filter Text Escaping

**Result: Rust is 1.9x faster**

`escape_filter_text` iterates character-by-character through strings, performing
conditional escaping of 8 special characters. This is the one operation where Rust
shows a clear advantage: the Rust implementation processes characters in a tight
loop with pre-allocated output buffer, while Python builds a list of strings and
joins them.

The speedup grows with string length and special character density. Test inputs
ranged from 40 to 500 characters with 0-50% special character density.

**Verdict**: Rust's advantage is real but modest. For strings under ~100 chars, the
FFI overhead nearly eliminates the benefit. The Rust implementation is justified
primarily for safety (guaranteed correct escaping) rather than performance.

#### 3. Range List Operations (merge_ranges, find_gaps)

**Result: Python is 3.4-4.8x faster**

`merge_ranges` and `find_gaps` involve O(n log n) sorting followed by linear merging.
The Python implementations work with lightweight tuples `(start, end)`, while the
Rust versions must convert lists of `TimeRange` Python objects into Rust types at the
FFI boundary. This conversion overhead dominates the actual sort+merge computation.

Notably, the Rust disadvantage shrinks slightly at larger input sizes (4.8x at 100
ranges vs 3.5x at 500 ranges), suggesting the Rust sort+merge is faster in isolation,
but the conversion overhead still outweighs it at these scales.

**Verdict**: Rust range operations are justified by type safety and correctness
guarantees (e.g., preventing invalid ranges), not by performance. For pure speed
with Python-native data, pure Python is faster at these scales.

#### 4. Path Validation

**Result: Python is 8.3x faster**

`validate_path` performs two checks: empty string and null byte presence. In Python
this is `if not path` and `if '\0' in path`. The Rust implementation performs the
same checks but pays the FFI crossing cost for each call.

**Verdict**: Validation operations are too simple to benefit from Rust. The Rust
implementation is justified by security guarantees (consistent validation at the
Rust layer) rather than performance.

## Key Insights

### 1. PyO3 FFI Overhead Is the Dominant Factor

For operations completing in microseconds, the PyO3 boundary crossing (object
conversion, GIL interaction, type checking) adds significant overhead that can
exceed the computation itself. This is not a Rust limitation but a Python-Rust
interop limitation.

### 2. Rust Wins Scale with Computation Intensity

The only benchmark where Rust is faster (escape_filter_text) involves iterating
through every character in multiple strings with conditional logic. As the ratio
of "work done" to "boundary crossings" increases, Rust's advantage grows.

### 3. Rust Justification Is Primarily Safety, Not Speed

For this project's operations, the Rust layer provides:

- **Type safety**: Invalid ranges, positions, and durations are caught at construction
- **Input sanitization**: FFmpeg filter escaping is guaranteed correct
- **Security**: Path validation prevents null byte injection at the Rust boundary
- **Correctness**: Range merging/gap detection is backed by Rust's type system

These safety properties justify the Rust layer even when pure Python would be faster.

### 4. When Rust Performance Would Matter

Rust would show clear performance benefits for:

- **Batch processing**: Processing thousands of frames/ranges in a single FFI call
- **FFmpeg filter graph construction**: Building complex filter strings in Rust
  without per-operation FFI crossings
- **Compute-heavy operations**: Image processing, waveform analysis, or other
  operations where computation time exceeds milliseconds

## Running the Benchmarks

```bash
uv run python -m benchmarks
```

Results are printed to stdout with per-operation statistics and a summary table.
