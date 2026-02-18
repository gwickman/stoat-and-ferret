# Implementation Plan: speed-builders

## Overview

Create a new `speed.rs` module implementing setpts (video speed) and atempo (audio speed) filter builders. The atempo builder automatically chains instances for speeds above 2.0x using log2 decomposition. Speed range validated to [0.25, 4.0] matching existing `validate_speed()`.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/speed.rs` | Create | setpts and atempo builders with auto-chaining |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Register `speed` submodule |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export speed types and PyO3 bindings |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add speed type stubs (via stub_gen) |
| `tests/test_pyo3_bindings.py` | Modify | Add Python-side speed builder tests |

## Test Files

`tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: setpts Builder

1. Create `rust/stoat_ferret_core/src/ffmpeg/speed.rs`
2. Define `SpeedControl` struct with `speed_factor: f64` and `drop_audio: bool`
3. Implement `SpeedControl::new(factor)` with validation [0.25, 4.0]
4. Implement `setpts_filter() -> Filter` — generates `setpts=(1.0/speed)*PTS` expression
5. Register module in `ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- speed
```

### Stage 2: atempo Builder with Auto-Chaining

1. Implement `atempo_chain(speed: f64) -> Vec<f64>` — computes chain of atempo values each within [0.5, 2.0]
2. For speed > 2.0: `N = floor(log2(speed))` stages of 2.0 + remainder
3. For speed < 0.5: `N = floor(log2(1/speed))` stages of 0.5 + remainder
4. Implement `atempo_filters() -> Vec<Filter>` — generates Filter instances for each chained atempo
5. Implement `drop_audio()` option — returns no atempo filters when enabled

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- speed
```

### Stage 3: Edge Cases and Validation

1. Handle 1.0x speed (no-op) — setpts is identity, atempo chain is empty
2. Handle boundary values: 0.25x, 0.5x, 2.0x, 4.0x
3. Add validation error messages for out-of-range values
4. Add proptest for speed range validation

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- speed
```

### Stage 4: PyO3 Bindings

1. Add `#[pyclass]` and `#[pymethods]` to `SpeedControl`
2. Use `PyRefMut<'_, Self>` for method chaining
3. Export via `lib.rs`
4. Regenerate stubs: `cargo run --bin stub_gen`
5. Verify stubs: `uv run python scripts/verify_stubs.py`
6. Add Python tests in `tests/test_pyo3_bindings.py`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen
uv run python scripts/verify_stubs.py
uv run pytest tests/test_pyo3_bindings.py -v
```

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- atempo chaining logic — well-documented formula, extensive test coverage. See `004-research/external-research.md` Section 3.

## Commit Message

```
feat(rust): add speed control filter builders with atempo auto-chaining

BL-041: setpts and atempo builders with automatic chaining for speeds
above 2.0x, validation for [0.25, 4.0] range, and PyO3 bindings.
```