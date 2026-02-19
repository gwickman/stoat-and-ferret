---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass (11 pre-existing errors, 0 new)
  pytest: pass (160 passed, 11 skipped)
  cargo_clippy: pass
  cargo_test: pass (307 tests + 97 doc-tests)
---
# Completion Report: 001-drawtext-builder

## Summary

Implemented a type-safe `DrawtextBuilder` for constructing FFmpeg drawtext filters with position presets, font styling, shadow effects, box backgrounds, and alpha animation via the expression engine. The builder produces `Filter` objects that integrate seamlessly with the existing `FilterChain` and `FilterGraph` composition APIs.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | Position options support absolute coordinates, centered, and margin-based placement | Pass |
| FR-002 | Styling covers font size, color, shadow offset/color, and box background | Pass |
| FR-003 | Alpha animation supports fade in/out with configurable duration using expression engine | Pass |
| FR-004 | Generated drawtext filters validated as syntactically correct FFmpeg syntax | Pass |
| FR-005 | Contract tests verify generated commands pass ffmpeg -filter_complex validation | Pass |

## Files Changed

### New Files
- `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs` — Core implementation (Position enum, DrawtextBuilder struct, PyO3 bindings, 37 unit tests + 2 proptests + 2 doc-tests)

### Modified Files
- `rust/stoat_ferret_core/src/ffmpeg/mod.rs` — Added `pub mod drawtext`
- `rust/stoat_ferret_core/src/lib.rs` — Registered `DrawtextBuilder` class in PyO3 module
- `src/stoat_ferret_core/__init__.py` — Added `DrawtextBuilder` to imports, fallback stub, and `__all__`
- `src/stoat_ferret_core/_core.pyi` — Added `DrawtextBuilder` class stub with full type annotations
- `stubs/stoat_ferret_core/_core.pyi` — Added `DrawtextBuilder` to manual stubs (verified via `verify_stubs.py`)
- `tests/test_pyo3_bindings.py` — Added `TestDrawtextBuilder` class (20 tests) and updated `test_all_exports_present`
- `tests/test_contract/test_ffmpeg_contract.py` — Added `TestDrawtextContract` class (5 contract tests)

## Implementation Details

### DrawtextBuilder API

**Rust (builder pattern):**
```rust
DrawtextBuilder::new("Hello")
    .font("monospace")
    .fontsize(24)
    .fontcolor("white")
    .position(Position::Center)
    .shadow(2, 2, "black")
    .box_background("black@0.5", 5)
    .alpha_fade(1.0, 0.5, 5.0, 0.5)
    .build()  // -> Filter
```

**Python (method chaining via PyO3):**
```python
DrawtextBuilder("Hello")
    .font("monospace")
    .fontsize(24)
    .fontcolor("white")
    .position("center")
    .shadow(2, 2, "black")
    .box_background("black@0.5", 5)
    .alpha_fade(1.0, 0.5, 5.0, 0.5)
    .build()  # -> Filter
```

### Position Presets
- `Center` — `x=(w-text_w)/2, y=(h-text_h)/2`
- `BottomCenter { margin }` — centered X, margin from bottom
- `TopLeft { margin }`, `TopRight { margin }`, `BottomLeft { margin }`, `BottomRight { margin }`
- `Absolute { x, y }` — direct pixel coordinates

### Text Escaping
Extended `escape_filter_text` with `%` -> `%%` for drawtext's text expansion mode. Handles all FFmpeg special characters: `\`, `'`, `:`, `[`, `]`, `;`, `\n`, `\r`, `%`.

### Alpha Animation
Uses the expression engine to generate nested `if(lt(t,...))` expressions for fade-in/fade-out patterns. The expression tree is serialized to valid FFmpeg syntax.

## Test Summary

- **Rust unit tests:** 37 tests covering escaping, position presets, styling, shadow, box, alpha, enable, builder integration
- **Rust property tests:** 2 proptests (arbitrary parameters, special character escaping)
- **Rust doc-tests:** 2 doc-tests
- **Python binding tests:** 20 tests covering all PyO3 methods, chaining, error cases, Filter integration
- **Contract tests:** 5 tests verifying FFmpeg accepts generated filter strings (skipped when FFmpeg unavailable)
