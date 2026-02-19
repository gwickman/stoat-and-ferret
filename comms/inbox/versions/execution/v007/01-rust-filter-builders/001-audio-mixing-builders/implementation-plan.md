# Implementation Plan: audio-mixing-builders

## Overview

Implement AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern as Rust filter builders with PyO3 bindings. Follows the proven v006 builder template (LRN-028). Creates a new `audio.rs` module under `rust/stoat_ferret_core/src/ffmpeg/`, registers PyO3 classes, generates type stubs, and adds comprehensive Rust unit tests and Python parity tests.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `rust/stoat_ferret_core/src/ffmpeg/audio.rs` | AmixBuilder, VolumeBuilder, AfadeBuilder, DuckingPattern, FadeCurve enum |
| Modify | `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Add `pub mod audio;` and re-exports |
| Modify | `rust/stoat_ferret_core/src/lib.rs` | Register new PyO3 classes in the module |
| Modify | `rust/stoat_ferret_core/src/sanitize/mod.rs` | Add `validate_fade_duration()` if needed |
| Modify | `stubs/stoat_ferret_core/_core.pyi` | Add type stubs for new builders |
| Create | `tests/test_audio_builders.py` | Python parity tests for audio builders |

## Test Files

`tests/test_audio_builders.py tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: VolumeBuilder and AfadeBuilder (single-input, simpler)

1. Create `audio.rs` with `FadeCurve` enum (12 variants: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par)
2. Implement `VolumeBuilder`: `#[pyclass]` struct, `#[new]` with validation via `validate_volume()` (0.0-10.0), fluent methods for `precision`, `.build()` returning `Filter`
3. Implement `AfadeBuilder`: `#[pyclass]` struct, `#[new]` with type (in/out) and duration, fluent methods for `start_time`, `curve`, `.build()` returning `Filter`
4. Add `pub mod audio;` to `ffmpeg/mod.rs` with re-exports
5. Register classes in `lib.rs`
6. Add Rust unit tests inline in `audio.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test audio && cargo clippy -- -D warnings
```

### Stage 2: AmixBuilder (multi-input)

1. Implement `AmixBuilder`: `#[new]` with input count (2-32), fluent methods for `duration_mode`, `weights`, `normalize`, `.build()` returning `Filter`
2. Add Rust unit tests for input count validation, weight assignment, duration modes

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test audio && cargo clippy -- -D warnings
```

### Stage 3: DuckingPattern (composite via FilterGraph)

1. Implement `DuckingPattern`: `#[new]` with threshold/ratio/attack/release parameters
2. `.build()` returns `FilterGraph` using composition API:
   - `compose_branch("0:a", 2, true)` for asplit
   - `compose_chain()` for sidechaincompress on sidechain branch
   - `compose_merge()` for amerge
3. Add Rust unit tests for parameter validation and FilterGraph composition

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test audio && cargo test ducking && cargo clippy -- -D warnings
```

### Stage 4: PyO3 bindings, stubs, and parity tests

1. Regenerate stubs: `cargo run --bin stub_gen`
2. Update `stubs/stoat_ferret_core/_core.pyi` with proper method signatures
3. Verify stubs: `uv run python scripts/verify_stubs.py`
4. Build extension: `maturin develop` (from project root)
5. Create `tests/test_audio_builders.py` with parity tests
6. Add edge case tests: silence, clipping prevention, format mismatches

**Verification:**
```bash
uv run python scripts/verify_stubs.py
uv run pytest tests/test_audio_builders.py tests/test_pyo3_bindings.py -v
```

## Test Infrastructure Updates

- New test file: `tests/test_audio_builders.py` for Python-side parity tests
- Extend `tests/test_pyo3_bindings.py` with audio builder import tests
- Rust coverage tracked before/after: `cargo tarpaulin --out Xml`

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- DuckingPattern FilterGraph composition may need debugging — see `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- FadeCurve enum with 12 variants needs exhaustive testing

## Commit Message

```
feat(rust): add audio mixing filter builders (amix, volume, afade, ducking)
```