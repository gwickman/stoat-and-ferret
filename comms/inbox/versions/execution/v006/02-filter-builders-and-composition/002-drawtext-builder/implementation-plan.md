# Implementation Plan: drawtext-builder

## Overview

Implement a structured drawtext filter builder in Rust supporting position modes, styling parameters, and alpha animation via the expression engine. Includes contract tests verifying generated filters pass `ffmpeg -filter_complex` validation using the existing record-replay infrastructure.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs` | Create | Drawtext builder with position, styling, alpha animation |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Add `pub mod drawtext;` declaration |
| `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | Modify | Import/use expression types for alpha animation (if not already public) |
| `rust/stoat_ferret_core/src/sanitize/mod.rs` | Modify | Use existing `escape_filter_text()` from drawtext builder (verify public access) |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Register drawtext types in PyO3 module |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add type stubs for drawtext builder types |
| `rust/stoat_ferret_core/tests/test_drawtext.rs` | Create | Unit tests for drawtext builder |
| `tests/test_contract/test_drawtext_contract.py` | Create | Contract tests with FFmpeg validation |

## Implementation Stages

### Stage 1: Drawtext Builder Core

1. Create `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs` with:
   - `DrawtextBuilder` struct with `PyRefMut` chaining (LRN-001)
   - Position enum: `Absolute(x, y)`, `Centered`, `Margin(top, right, bottom, left)`
   - Position serialization to drawtext `x` and `y` parameters
2. Add `pub mod drawtext;` to `rust/stoat_ferret_core/src/ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_drawtext
```

### Stage 2: Styling Parameters

1. Add styling methods to DrawtextBuilder:
   - `font_size(size: u32)`
   - `font_color(color: &str)` with validation
   - `shadow_offset(x: i32, y: i32)`, `shadow_color(color: &str)`
   - `box_enabled(enabled: bool)`, `box_color(color: &str)`, `box_border_width(width: u32)`
2. Text content via `text(content: &str)` using `escape_filter_text()` from sanitize module

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_drawtext
```

### Stage 3: Alpha Animation

1. Integrate with expression engine (Theme 01, Feature 001):
   - `fade_in(start: f64, duration: f64)` → generates `alpha='min(1, (t-{start})/{duration})'`
   - `fade_out(end: f64, duration: f64)` → generates alpha fade-out expression
   - `enable_window(start: f64, end: f64)` → generates `enable='between(t, {start}, {end})'`
2. Uses expression builder from `ffmpeg::expression` module

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_drawtext
```

### Stage 4: PyO3 Bindings and Type Stubs

1. Add `#[pyclass]` and `#[pymethods]` to DrawtextBuilder
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
uv run python -c "from stoat_ferret_core import DrawtextBuilder"
uv run python scripts/verify_stubs.py
```

### Stage 5: Contract Tests

1. Create `tests/test_contract/test_drawtext_contract.py` with:
   - Record-replay tests using `RecordingFFmpegExecutor`/`FakeFFmpegExecutor` (LRN-008)
   - Tests verify generated drawtext filters pass `ffmpeg -filter_complex` validation
   - Use `@pytest.mark.contract` and `@requires_ffmpeg` markers
   - Test basic text, styled text, animated text filter strings

**Verification:**
```bash
uv run pytest tests/test_contract/test_drawtext_contract.py -v
```

## Test Infrastructure Updates

- New contract test file follows existing patterns in `tests/test_contract/`
- Uses existing `@pytest.mark.contract` and `@requires_ffmpeg` markers from `pyproject.toml`

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Depends on Theme 01 Feature 001 (expression-engine) for alpha animation. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.
- Contract tests require FFmpeg — available on all CI entries via `AnimMouse/setup-ffmpeg@v1`.

## Commit Message

```
feat: implement drawtext filter builder with contract tests

Add structured drawtext builder supporting position modes, font/color/
shadow/box styling, and alpha animation via expression engine. Contract
tests verify generated filters pass ffmpeg -filter_complex. Covers BL-040.
```