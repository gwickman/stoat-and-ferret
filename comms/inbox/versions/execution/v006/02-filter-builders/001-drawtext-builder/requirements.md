# Requirements: drawtext-builder

## Goal

Type-safe drawtext filter builder with position presets, styling, and alpha animation via expression engine.

## Background

Backlog Item: BL-040

The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping — a frequent source of FFmpeg errors.

## Functional Requirements

### FR-001: Position Options

Position options support absolute coordinates, centered, and margin-based placement. Position presets: center (`x=(w-text_w)/2:y=(h-text_h)/2`), bottom-center (`x=(w-text_w)/2:y=h-text_h-10`), top-left margin (`x=10:y=10`). Expression variables available: `w`, `h`, `text_w`, `text_h`, `line_h`, `main_w`, `main_h`.

**Acceptance criteria:** Position options support absolute coordinates, centered, and margin-based placement.

### FR-002: Styling

Styling covers font size (default 16), color (default "black"), shadow offset/color (`shadowx`, `shadowy`, `shadowcolor`), and box background (`box`, `boxcolor`, `boxborderw`). Font via both `font(name)` (fontconfig, cross-platform) and `fontfile(path)` (explicit path). Single-value `boxborderw(width: u32)` only — no pipe-delimited per-side syntax.

**Acceptance criteria:** Styling covers font size, color, shadow offset/color, and box background.

### FR-003: Alpha Animation

Alpha animation supports fade in/out with configurable duration using expression engine. Pattern: `alpha='if(lt(t,T1),0,if(lt(t,T1+FI),(t-T1)/FI,if(lt(t,T2-FO),1,if(lt(t,T2),(T2-t)/FO,0))))'`. Alpha range [0.0, 1.0].

**Acceptance criteria:** Alpha animation supports fade in/out with configurable duration using expression engine.

### FR-004: Syntax Validation

Generated drawtext filters validated as syntactically correct FFmpeg syntax. Text escaping handles `\`, `'`, `:`, `[`, `]`, `;`, `%` (extending existing `escape_filter_text()` with `%` -> `%%` for text expansion mode).

**Acceptance criteria:** Generated drawtext filters validated as syntactically correct FFmpeg syntax.

### FR-005: Contract Tests

Contract tests verify generated commands pass `ffmpeg -filter_complex` validation using FFmpeg binary (already available in CI).

**Acceptance criteria:** Contract tests verify generated commands pass ffmpeg -filter_complex validation.

## Non-Functional Requirements

### NFR-001: Test Coverage

New drawtext module targets >90% coverage. CI threshold remains at 75%.

### NFR-002: Cross-Platform Tests

Tests use `font("monospace")` (fontconfig-based, cross-platform). No platform detection logic in the builder.

## Out of Scope

- Per-side `boxborderw` syntax (FFmpeg 5.0+ only — deferred)
- Text expansion with strftime (`%{localtime}` patterns)
- Animated position (scrolling text)
- Multiple text overlays in a single builder call

## Test Requirements

- Unit tests for each position preset
- Unit tests for styling parameters (font, color, shadow, box)
- Unit tests for alpha animation expression generation
- Contract tests with FFmpeg binary validation
- Proptest for drawtext parameter combinations
- PyO3 binding tests
- Type stub regeneration and verification

## Sub-tasks

- Impact #4: Run `cargo run --bin stub_gen` after adding PyO3 bindings

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.