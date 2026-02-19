# Theme Retrospective: 02-filter-builders

**Version:** v006
**Theme:** 02-filter-builders
**Status:** Complete (2/2 features, 10/10 acceptance criteria passed)
**Execution Window:** 2026-02-19

---

## 1. Theme Summary

This theme implemented the user-facing filter builders for text overlay and speed control, building directly on the expression engine, filter graph, and composition APIs from Theme 01. The two features — `DrawtextBuilder` and `SpeedControl` — provide type-safe Rust structs with builder-pattern APIs exposed to Python via PyO3, producing `Filter` objects that integrate with the existing `FilterChain` and `FilterGraph` composition system.

Both features completed on first iteration with all quality gates passing and all 10 acceptance criteria met. The theme corresponds to milestones M2.2 (Text Overlay) and M2.3 (Speed Control) in the project roadmap.

---

## 2. Feature Results

| Feature | Acceptance | Quality Gates | Iteration | Key Deliverable |
|---------|-----------|---------------|-----------|-----------------|
| 001-drawtext-builder | 5/5 PASS | All pass | 1 | `DrawtextBuilder` with position presets, font styling, shadow/box effects, alpha fade animation via expression engine |
| 002-speed-builders | 5/5 PASS | All pass | 1 | `SpeedControl` with setpts video speed, atempo audio speed with automatic chaining, drop-audio option |

### Test Growth Across Features

| Feature | Rust Tests | Rust Doc Tests | Rust Proptests | Python Tests | pytest Total |
|---------|-----------|----------------|----------------|-------------|-------------|
| 001-drawtext-builder | 37 | 2 | 2 | 20 | 160 passed |
| 002-speed-builders | 41 | 4 | 4 | 24 | 708 passed |

### Quality Gate Summary

| Gate | 001-drawtext-builder | 002-speed-builders |
|------|---------------------|-------------------|
| ruff | Pass | Pass |
| mypy | Pass (0 new errors) | Pass (0 new errors) |
| pytest | 160 passed, 11 skipped | 708 passed, 20 skipped |
| cargo clippy | Pass | Pass |
| cargo test | 307 tests + 97 doc-tests | 41 unit + 4 doc + 4 proptests |

---

## 3. Key Learnings

### What Worked Well

- **Theme 01 foundations were solid**: Both builders built directly on `Expr`, `Filter`, `FilterChain`, and the composition APIs with no rework needed. The expression engine's `if(lt(t,...))` pattern enabled alpha fade animations out of the box.

- **Builder pattern consistency**: Both features followed the same pattern — Rust builder struct with `build() -> Filter`, PyO3 method chaining, type stubs, Python binding tests, contract tests. This made the second feature faster to implement than the first.

- **Positional filter syntax decision (002)**: Using `Filter::new(format!("setpts={expr}"))` instead of named parameters was the correct call for FFmpeg's positional syntax expectations. This avoided subtle bugs where FFmpeg would reject `setpts=expr=0.5*PTS`.

- **Reusing existing validation**: SpeedControl leveraged the existing `sanitize::validate_speed()` for range checking rather than duplicating validation logic, keeping the codebase DRY.

- **Atempo chaining algorithm**: The decomposition approach for speeds outside [0.5, 2.0] (chaining multiple atempo filters) is both correct and well-tested with proptests verifying chain product correctness and individual value bounds.

### Patterns Discovered

- **Text escaping for drawtext**: Extended `escape_filter_text` with `%` → `%%` handling for drawtext's text expansion mode. This is a drawtext-specific concern beyond standard FFmpeg filter escaping.

- **Position presets as enum**: Encoding common positions (Center, BottomCenter, TopLeft, etc.) as an enum with margin parameters provides a much better API than raw coordinate pairs while still supporting `Absolute { x, y }` for full control.

- **Clean number formatting**: Custom `format_pts_multiplier()` and `format_tempo_value()` helpers produce human-readable output (`0.5*PTS` instead of `0.500000*PTS`), improving debuggability of generated FFmpeg commands.

---

## 4. Technical Debt

No quality-gaps files were generated for either feature, indicating clean implementations. Items to note:

- **Stub regeneration fragility (002)**: The 002-speed-builders completion report notes stubs were "auto-regenerated" rather than manually extended. Per project conventions, `cargo run --bin stub_gen` strips method bodies and may lose hand-written content. The `verify_stubs.py` script caught any drift, but this remains a manual coordination point.

- **Pre-existing mypy errors**: Both features report 11 pre-existing mypy errors. These are not regressions from this theme but should be tracked for eventual cleanup.

- **Contract tests require FFmpeg**: The drawtext contract tests (5 tests) are skipped when FFmpeg is unavailable. CI environments without FFmpeg will not exercise these validation paths.

---

## 5. Recommendations

### For Theme 03 (effects-api)

- The `DrawtextBuilder` and `SpeedControl` builders produce `Filter` objects ready for API consumption. The API layer should accept builder configuration parameters and delegate to these builders.
- Consider exposing builder defaults (e.g., default position, default font) as API-level configuration to reduce required parameters for common use cases.
- The filter chain integration is already tested — API endpoints can compose multiple effects using `FilterChain` and `FilterGraph` directly.

### For Future Similar Themes

- **Single-iteration success continues**: Both themes (01 and 02) completed all features on first iteration, confirming that well-specified design documents and acceptance criteria lead to clean execution.
- **Builder pattern is proven**: The Rust builder → PyO3 bindings → stub → Python tests pattern has now been validated across 5 features. New builders (e.g., crop, scale, overlay) should follow this exact template.
- **Proptest investment pays off**: Property-based tests in both features caught real edge cases (expression correctness, atempo chain bounds). The marginal cost of adding proptests is low compared to the bugs they prevent.
- **pytest total growth**: The jump from 664 (end of theme 01) to 708 (end of theme 02) shows healthy additive test growth with no test churn or regressions.
