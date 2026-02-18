# Implementation Plan: drawtext-builder

## Overview

Create a new `drawtext.rs` module implementing a type-safe drawtext filter builder with position presets, font/styling, shadow, box background, and alpha animation using the expression engine from Theme 01. Includes contract tests that verify generated filter strings against FFmpeg binary.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs` | Create | Drawtext builder with position presets, styling, alpha animation |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Register `drawtext` submodule |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export drawtext types and PyO3 bindings |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add drawtext type stubs (via stub_gen) |
| `tests/test_pyo3_bindings.py` | Modify | Add Python-side drawtext tests |
| `tests/test_contract/test_ffmpeg_contract.py` | Modify | Add drawtext contract tests |

## Test Files

`tests/test_pyo3_bindings.py tests/test_contract/test_ffmpeg_contract.py`

## Implementation Stages

### Stage 1: Core Drawtext Builder

1. Create `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs`
2. Define `DrawtextBuilder` struct with builder pattern
3. Implement `text(str)` — mandatory, with escaping (extend `escape_filter_text()` with `%` -> `%%`)
4. Implement `font(name)` and `fontfile(path)` methods
5. Implement `fontsize(u32)` (default 16), `fontcolor(str)` (default "black")
6. Implement `build() -> Filter` — generates drawtext filter using existing `Filter::new("drawtext").param()` API
7. Register module in `ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- drawtext
```

### Stage 2: Position Presets and Shadow/Box

1. Define `Position` enum: `Absolute { x, y }`, `Center`, `BottomCenter { margin }`, `TopLeft { margin }`, `TopRight { margin }`, `BottomLeft { margin }`, `BottomRight { margin }`
2. Implement `position(Position)` method generating x/y expression strings
3. Implement `shadow(x_offset, y_offset, color)` method
4. Implement `box_background(color, borderw)` method — single-value `boxborderw` only

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- drawtext
```

### Stage 3: Alpha Animation

1. Implement `alpha(f64)` for static alpha
2. Implement `alpha_fade(start_time, fade_in, end_time, fade_out)` — generates expression using `Expr` types from expression engine
3. Alpha fade pattern: `if(lt(t,T1),0,if(lt(t,T1+FI),(t-T1)/FI,if(lt(t,T2-FO),1,if(lt(t,T2),(T2-t)/FO,0))))`
4. Implement `enable(expr)` for time-based enabling

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- drawtext
```

### Stage 4: PyO3 Bindings and Contract Tests

1. Add `#[pyclass]` and `#[pymethods]` to `DrawtextBuilder`
2. Use `PyRefMut<'_, Self>` for method chaining
3. Export via `lib.rs`
4. Regenerate stubs: `cargo run --bin stub_gen`
5. Verify stubs: `uv run python scripts/verify_stubs.py`
6. Add Python tests in `tests/test_pyo3_bindings.py`
7. Add contract tests in `tests/test_contract/test_ffmpeg_contract.py` — generate drawtext filter string, run through `ffmpeg -filter_complex` validation

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen
uv run python scripts/verify_stubs.py
uv run pytest tests/test_pyo3_bindings.py tests/test_contract/test_ffmpeg_contract.py -v
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

- Font handling cross-platform — mitigate with `font()` (fontconfig) and `fontfile()` support; tests use `font("monospace")`. See `006-critical-thinking/risk-assessment.md`.
- boxborderw version dependency — mitigate with single-value only. See `006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat(rust): add drawtext filter builder with position presets and alpha animation

BL-040: Type-safe drawtext builder with position presets, styling, shadow,
box background, and alpha animation via expression engine.
```