# Theme: filter-builders

## Goal

Implement concrete filter builders for text overlay and speed control using the expression engine from Theme 01. These are the user-facing effect implementations that the API layer will expose. Corresponds to M2.2 (Text Overlay) and M2.3 (Speed Control).

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | drawtext-builder | BL-040 | Type-safe drawtext filter builder with position presets, styling, and alpha animation via expression engine |
| 002 | speed-builders | BL-041 | setpts and atempo filter builders with automatic atempo chaining for speeds above 2.0x |

## Dependencies

- Theme 01 `001-expression-engine` must be complete (both builders consume the expression engine)
- Features within this theme are independent of each other

## Technical Approach

- **Drawtext builder (BL-040):** Extend existing builder pattern (`Filter::new().param()`) with typed methods for position presets, font/styling, shadow, box, and alpha animation. Alpha animation delegates to expression engine (`between`, `if`, `lt` patterns). Supports both `font()` (fontconfig) and `fontfile()` (explicit path). Single-value `boxborderw` only. See `004-research/external-research.md` Section 2.
- **Speed builders (BL-041):** `setpts` filter with formula `PTS * (1.0/speed)`. `atempo` filter with automatic chaining for speeds above 2.0x using log2 decomposition. Speed range [0.25, 4.0] matching existing `validate_speed()`. Option to drop audio. See `004-research/external-research.md` Section 3.

## Risks

| Risk | Mitigation |
|------|------------|
| Font file platform dependency | Builder supports both `font()` and `fontfile()`; tests use fontconfig. See `006-critical-thinking/risk-assessment.md` |
| boxborderw FFmpeg version | Single-value `boxborderw` only; defer per-side syntax. See `006-critical-thinking/risk-assessment.md` |