# Requirements: drawtext-builder

## Goal

Implement a drawtext filter builder with position, styling, alpha animation, and contract tests.

## Background

Backlog Item: BL-040

The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping — a frequent source of FFmpeg errors.

## Functional Requirements

**FR-001: Position options**
- Support absolute coordinates, centered placement, and margin-based positioning
- AC: Each position mode generates correct drawtext `x` and `y` parameters

**FR-002: Styling parameters**
- Cover font size, color, shadow offset/color, and box background
- AC: All styling parameters serialize to valid drawtext filter syntax

**FR-003: Alpha animation**
- Support fade in/out with configurable duration using the expression engine (Theme 01, Feature 001)
- Fade-in: `alpha='min(1, (t-start)/fade_duration)'`
- Enable window: `enable='between(t, start, end)'`
- AC: Generated alpha and enable expressions are valid FFmpeg expressions

**FR-004: Filter syntax validation**
- Generated drawtext filters validated as syntactically correct FFmpeg syntax
- AC: Builder output passes FFmpeg syntax validation

**FR-005: Contract tests**
- Verify generated commands pass `ffmpeg -filter_complex` validation
- Use record-replay pattern (LRN-008) with existing `RecordingFFmpegExecutor`/`FakeFFmpegExecutor`
- AC: Contract tests pass with both recorded and real FFmpeg execution

**FR-006: Text escaping**
- Use existing `escape_filter_text()` from Rust sanitize module for text content
- AC: Special characters in text content are correctly escaped in generated filters

**FR-007: PyO3 bindings**
- Expose drawtext builder to Python with type stubs
- Builder pattern with `PyRefMut` chaining (LRN-001)
- AC: Python code can build drawtext filters identically to Rust

## Non-Functional Requirements

**NFR-001: Test coverage**
- Module-level Rust coverage >90%
- AC: `cargo tarpaulin` reports >90% for the drawtext module

**NFR-002: Contract test CI**
- Contract tests run on all CI matrix entries (FFmpeg available via `AnimMouse/setup-ffmpeg@v1`)
- AC: Contract tests pass on ubuntu/macos/windows CI entries

## Out of Scope

- Dynamic text content (e.g., timecode overlay — v007 concern)
- Multiple simultaneous text overlays in a single builder call
- Font file management or embedding

## Test Requirements

- **Unit tests:** Position options (absolute, centered, margin), styling parameters (font, color, shadow, box), alpha animation (fade in/out expression generation), PyO3 bindings (builder from Python)
- **Contract tests:** Generated drawtext filters pass `ffmpeg -filter_complex` validation using record-replay pattern

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`
