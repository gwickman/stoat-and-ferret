# Implementation Plan: transition-filter-builders

## Overview

Implement FadeBuilder, XfadeBuilder with TransitionType enum, and AcrossfadeBuilder as Rust filter builders with PyO3 bindings. FadeBuilder is a single-input video fade. XfadeBuilder and AcrossfadeBuilder are two-input filters using the existing `FilterChain.input()` multi-input pattern. Creates a new `transitions.rs` module.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `rust/stoat_ferret_core/src/ffmpeg/transitions.rs` | FadeBuilder, XfadeBuilder, TransitionType enum, AcrossfadeBuilder |
| Modify | `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Add `pub mod transitions;` and re-exports |
| Modify | `rust/stoat_ferret_core/src/lib.rs` | Register new PyO3 classes and TransitionType enum |
| Modify | `stubs/stoat_ferret_core/_core.pyi` | Add type stubs for transition builders and enum |
| Create | `tests/test_transition_builders.py` | Python parity tests for transition builders |

## Test Files

`tests/test_transition_builders.py tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: TransitionType enum and FadeBuilder (single-input)

1. Create `transitions.rs` with `TransitionType` enum (64 variants from FFmpeg xfade)
2. Implement `from_str`/`to_string` for TransitionType with round-trip correctness
3. Implement `FadeBuilder`: `#[new]` with type (in/out) and duration, fluent methods for `color`, `alpha`, `start_time`, `nb_frames`, `.build()` returning `Filter`
4. Add `pub mod transitions;` to `ffmpeg/mod.rs` with re-exports
5. Register classes in `lib.rs`
6. Add Rust unit tests for enum variants and FadeBuilder

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test transitions && cargo clippy -- -D warnings
```

### Stage 2: XfadeBuilder (two-input)

1. Implement `XfadeBuilder`: `#[new]` with `TransitionType`, duration (0.0-60.0), offset
2. `.build()` creates a two-input `FilterChain`: `FilterChain::new().input(label1).input(label2).filter(xfade).output(out)`
3. Duration validation rejects < 0 or > 60 with `PyValueError`
4. Add Rust unit tests for all transition types, duration range, two-input pattern

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test xfade && cargo clippy -- -D warnings
```

### Stage 3: AcrossfadeBuilder (two-input audio)

1. Implement `AcrossfadeBuilder`: `#[new]` with duration, fluent methods for `curve1`, `curve2` (reuse FadeCurve enum from audio.rs), `overlap`
2. Two-input filter chain pattern
3. Add Rust unit tests

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test acrossfade && cargo clippy -- -D warnings
```

### Stage 4: PyO3 bindings, stubs, and parity tests

1. Regenerate stubs: `cargo run --bin stub_gen`
2. Update `stubs/stoat_ferret_core/_core.pyi` with transition builder and enum signatures
3. Verify stubs: `uv run python scripts/verify_stubs.py`
4. Build extension: `maturin develop` (from project root)
5. Create `tests/test_transition_builders.py` with parity tests
6. Add parameter validation error message tests

**Verification:**
```bash
uv run python scripts/verify_stubs.py
uv run pytest tests/test_transition_builders.py tests/test_pyo3_bindings.py -v
```

## Test Infrastructure Updates

- New test file: `tests/test_transition_builders.py` for Python parity tests
- Extend `tests/test_pyo3_bindings.py` with transition builder import tests
- Track Rust coverage after T01 completion: `cargo tarpaulin --out Xml`

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- TransitionType enum with 64 variants is large — consider macro generation. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- AcrossfadeBuilder reuses FadeCurve from audio.rs — ensure module visibility

## Commit Message

```
feat(rust): add transition filter builders (fade, xfade, acrossfade)
```