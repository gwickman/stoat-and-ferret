# Implementation Plan: speed-control

## Overview

Implement setpts (video speed) and atempo (audio speed) builders in Rust with 0.25x-4.0x range, automatic atempo chaining for >2x factors, audio drop option, and validation. This is a focused Rust module independent of the expression engine.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `rust/stoat_ferret_core/src/ffmpeg/speed.rs` | Create | setpts and atempo builder types |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Add `pub mod speed;` declaration |
| `rust/stoat_ferret_core/src/sanitize/mod.rs` | Modify | Use existing `validate_speed()` (verify public access) |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Register speed types in PyO3 module |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add type stubs for speed control types |
| `rust/stoat_ferret_core/tests/test_speed.rs` | Create | Unit tests for speed control |

## Implementation Stages

### Stage 1: setpts Video Speed Builder

1. Create `rust/stoat_ferret_core/src/ffmpeg/speed.rs` with:
   - `SpeedControlBuilder` struct with `PyRefMut` chaining (LRN-001)
   - `fn video_speed(factor: f64) -> Result<Filter, SpeedError>`
   - Generates `setpts=PTS/{factor}` expression
   - Uses `validate_speed()` from sanitize module for 0.25-4.0 range validation
2. Add `pub mod speed;` to `rust/stoat_ferret_core/src/ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_speed
```

### Stage 2: atempo Audio Speed Builder

1. Add audio speed methods:
   - `fn audio_speed(factor: f64) -> Result<Vec<Filter>, SpeedError>`
   - Single atempo filter for factors <=2.0x
   - Automatic chaining for factors >2.0x: decompose into chained atempo filters
     - Example: 3.0x → `atempo=2.0,atempo=1.5`
     - Example: 4.0x → `atempo=2.0,atempo=2.0`
2. Add audio drop option:
   - `fn drop_audio() -> Self` — generates video-only speed filter (no atempo)

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_speed
```

### Stage 3: Edge Cases and Validation

1. Handle edge cases:
   - 1.0x factor: no-op (identity filter or skip)
   - Boundary values: 0.25x, 4.0x
   - Out-of-range: reject with helpful error messages
2. Error messages from `validate_speed()` surface clearly

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_speed
```

### Stage 4: PyO3 Bindings and Type Stubs

1. Add `#[pyclass]` and `#[pymethods]` to SpeedControlBuilder
   - `py_` prefix with `#[pyo3(name = "...")]` convention
   - `#[gen_stub_pyclass]` annotations
2. Register in `lib.rs` PyO3 module
3. Generate and update stubs:
   ```bash
   cd rust/stoat_ferret_core && cargo run --bin stub_gen
   ```

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test
uv run python -c "from stoat_ferret_core import SpeedControlBuilder"
uv run python scripts/verify_stubs.py
```

## Test Infrastructure Updates

- No new test infrastructure needed — standard Rust unit tests

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Atempo chaining decomposition correctness — mitigate with comprehensive edge case tests. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: implement speed control filter builders (setpts/atempo)

Add setpts video speed and atempo audio speed builders with 0.25x-4.0x
range, automatic atempo chaining for >2x factors, audio drop option,
and validation. Covers BL-041.
```
