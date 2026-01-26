# Design Research Gaps - Exploration Summary

The v002 design foundations are largely solid, with most Rust types implemented and exposed to Python. Key findings reveal that Clip exists but is NOT exposed via PyO3, ValidationError has the expected structure, and TimeRange list operations (find_gaps, merge_ranges) exist in Rust but are also NOT exposed to Python.

## Question Answers

| # | Question | Status | Answer Summary | Details |
|---|----------|--------|----------------|---------|
| 1 | Clip module status | EXISTS, NOT EXPOSED | `Clip` struct exists with full API but has no PyO3 bindings | [rust-types.md](rust-types.md#clip-module) |
| 2 | ValidationError structure | COMPLETE | Has `field`, `message`, `actual`, `expected` attributes | [rust-types.md](rust-types.md#validationerror) |
| 3 | TimeRange list operations | EXISTS, NOT EXPOSED | `find_gaps`, `merge_ranges`, `total_coverage` exist in Rust, not exposed | [rust-types.md](rust-types.md#timerange-list-operations) |
| 4 | py_ prefix inventory | DOCUMENTED | 54 py_ methods across 7 files, all for PyO3 method chaining | [rust-types.md](rust-types.md#py_-prefix-inventory) |
| 5 | Stub generation binary | EXISTS | `stub_gen.rs` binary uses pyo3-stub-gen correctly | [stub-generation.md](stub-generation.md#binary-setup) |
| 6 | Repository pattern scope | UNSPECIFIED | Roadmap M1.4 says "repository pattern" generically, no specifics | [design-clarifications.md](design-clarifications.md#repository-pattern) |
| 7 | FFmpeg executor boundary | CLARIFIED | Rust builds command, Python executes subprocess | [design-clarifications.md](design-clarifications.md#ffmpeg-executor) |
| 8 | Prometheus client | SPECIFIED | `prometheus-client` library in dependencies section | [design-clarifications.md](design-clarifications.md#prometheus-client) |
| 9 | Python dependencies | MINIMAL | Only dev deps (pytest, ruff, mypy, maturin) - no runtime deps yet | [design-clarifications.md](design-clarifications.md#python-dependencies) |
| 10 | pyo3-stub-gen usage | CONFIGURED | pyo3-stub-gen 0.17 in Cargo.toml, binary exists, stubs generated | [stub-generation.md](stub-generation.md#configuration) |

## Critical Gaps for v002

1. **Clip type NOT exposed to Python** - The `Clip` struct exists in Rust with validation logic but has no `#[pyclass]` or `#[pymethods]`. This needs PyO3 bindings.

2. **TimeRange list operations NOT exposed** - `find_gaps`, `merge_ranges`, and `total_coverage` functions exist in Rust but are not registered in `lib.rs` for Python access.

3. **Repository pattern scope unclear** - The roadmap mentions "injectable storage interfaces" but doesn't specify whether VideoRepository handles videos+metadata+thumbnails together or separately.

4. **No runtime Python dependencies** - pyproject.toml has no runtime dependencies yet. v002 will need to add FastAPI, pydantic-settings, structlog, prometheus-client, etc.

## Stubs vs Rust API Discrepancies

The manual stubs in `stubs/stoat_ferret_core/_core.pyi` have some discrepancies with the actual Rust implementation:

- Stubs list `Position.from_timecode()` which doesn't exist in Rust
- Stubs list `Duration.__add__` which doesn't exist in Rust
- Stubs list `FrameRate.ntsc_30()` which is `fps_29_97()` in Rust
- Stubs missing the actual Python method names (e.g., `from_secs`, `as_secs`)

## Files

- [rust-types.md](rust-types.md) - Clip, ValidationError, TimeRange operations, py_ inventory
- [stub-generation.md](stub-generation.md) - How stubs work, what's in src/bin/, CI verification needs
- [design-clarifications.md](design-clarifications.md) - Repository scope, FFmpeg boundary, dependencies
