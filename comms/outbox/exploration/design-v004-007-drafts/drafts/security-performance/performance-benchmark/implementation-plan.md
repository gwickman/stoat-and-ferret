# Implementation Plan — performance-benchmark

## Overview

Create benchmark scripts comparing Rust vs Python implementations for representative operations, documenting speedup ratios.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `benchmarks/__init__.py` | Package init |
| Create | `benchmarks/run_benchmarks.py` | Main benchmark runner |
| Create | `benchmarks/bench_timeline.py` | Timeline arithmetic benchmarks |
| Create | `benchmarks/bench_filter_escape.py` | Filter string escaping benchmarks |
| Create | `benchmarks/bench_validation.py` | Path/input validation benchmarks |
| Create | `docs/design/10-performance-benchmarks.md` | Results documentation |

## Implementation Stages

### Stage 1: Benchmark Infrastructure
Create `benchmarks/` directory with `run_benchmarks.py` entry point. Implement timing utility with warmup, multiple iterations, and statistical summary (mean, median, std).

### Stage 2: Python Reference Implementations
Write pure-Python equivalents for operations currently handled by Rust: timeline position arithmetic, filter text escaping, input validation. These are reference implementations for comparison only.

### Stage 3: Benchmark Execution
Run each operation N times (e.g., 1000 iterations) with warmup. Measure Rust (via PyO3) vs Python for same inputs. Calculate speedup ratio.

### Stage 4: Results Documentation
Publish `docs/design/10-performance-benchmarks.md` with methodology, results table, speedup ratios, and analysis of whether Rust justifies the complexity for each operation.

## Quality Gates

- At least 3 benchmark comparisons
- Results document complete with no placeholder text
- Benchmarks runnable via `uv run python benchmarks/run_benchmarks.py`
- `uv run ruff check benchmarks/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Rust speedup negligible for some operations | Document honestly — not all operations need Rust |
| PyO3 call overhead dominates small operations | Batch operations if needed; document overhead |

## Commit Message

```
feat: add Rust vs Python performance benchmarks with results
```
