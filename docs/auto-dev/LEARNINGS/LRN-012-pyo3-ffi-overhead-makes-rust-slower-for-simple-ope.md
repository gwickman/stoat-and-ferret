## Context

It's tempting to assume Rust will be faster than Python for all operations in a hybrid architecture. However, the FFI boundary introduces overhead that dominates for simple operations.

## Learning

PyO3 FFI overhead makes Rust 7-10x slower than Python for simple arithmetic and validation operations, and 3.5-4.8x slower for simple range operations. Rust is only faster for string-heavy processing (1.9x faster for `escape_filter_text`). Use Rust for operations where it provides clear computational or safety value, not as a blanket performance optimization.

## Evidence

- v004 Theme 04 Feature 002 (performance-benchmark): 7 benchmarks across 4 categories with consistent methodology (100 warmup, 10 runs, mean/median/stdev).
- Timeline arithmetic: Rust 7-10x slower due to FFI overhead.
- Range operations: Rust 3.5-4.8x slower.
- Path validation: Rust 8.3x slower.
- String escaping: Rust 1.9x faster (the one case where Rust wins on performance).

## Application

- Profile before assuming Rust will be faster — FFI overhead is significant for simple operations.
- Reserve Rust for operations where safety, correctness, or string processing justify the overhead.
- For performance-sensitive hot paths with simple logic, Python-native implementations may be faster.
- Use benchmarks with seeded random data for reproducible performance comparisons.