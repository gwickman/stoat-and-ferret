# Requirements — performance-benchmark

## Goal

Benchmark Rust vs Python for 3+ representative operations with documented speedup ratios.

## Background

M1.9 requires benchmarking Rust core operations against pure-Python equivalents to validate the hybrid architecture. No benchmark infrastructure exists. Candidate operations identified in research: timeline position arithmetic, filter string escaping, path validation. Final selection at implementation time after profiling (U2 TBD).

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | Benchmark script compares Rust vs Python for at least 3 representative operations | BL-026 |
| FR-2 | Results documented with speedup ratios for each operation | BL-026 |
| FR-3 | Benchmark runnable via `uv run python benchmarks/` command | BL-026 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Benchmarks use consistent methodology (multiple runs, warmup, statistical summary) |
| NFR-2 | Results reproducible on different machines (relative ratios, not absolute times) |
| NFR-3 | No benchmark dependency on external resources (FFmpeg, network) |

## Out of Scope

- Continuous benchmark regression tracking in CI
- Micro-optimization of Rust or Python code based on findings
- Benchmarking FFmpeg operations (those are I/O-bound, not compute)

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Benchmark | Rust vs Python: at least 3 representative operations | 3–5 |
| (none) | Benchmark scripts are not pytest tests — runnable separately | — |
