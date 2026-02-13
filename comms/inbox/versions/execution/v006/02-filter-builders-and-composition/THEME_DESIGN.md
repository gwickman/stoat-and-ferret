# Theme: filter-builders-and-composition

## Goal

Build the concrete filter builders (drawtext for text overlays, speed control for setpts/atempo) and the composition system for chaining, branching, and merging filter graphs. These features consume Theme 01's infrastructure and produce the Rust-side building blocks that the API layer (Theme 03) needs.

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.
See `comms/outbox/versions/design/v006/005-logical-design/test-strategy.md` for test requirements.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | filter-composition | BL-039 | Build chain/branch/merge composition API with automatic pad management and validation |
| 002 | drawtext-builder | BL-040 | Implement drawtext filter builder with position, styling, alpha animation, and contract tests |
| 003 | speed-control | BL-041 | Implement setpts/atempo builders with automatic atempo chaining for speeds above 2x |

## Dependencies

- Theme 01, Feature 001 (expression-engine) must be complete before Feature 002 (drawtext-builder) — alpha animation uses expression engine
- Theme 01, Feature 002 (graph-validation) must be complete before Feature 001 (filter-composition) — composition uses graph validation

Feature 003 (speed-control) is independent within the theme.

## Technical Approach

**Filter composition (BL-039):**
- Chain mode: sequential filters on a single stream with automatic pad label management
- Branch mode: split one stream into multiple output streams
- Merge mode: combine streams via overlay, amix, or concat
- Composed graphs validated automatically via Theme 01's graph validation
- Builder API uses `PyRefMut` chaining pattern (LRN-001)

**Drawtext builder (BL-040):**
- Structured builder supporting absolute/centered/margin-based positioning
- Font/color/shadow/box styling parameters
- Alpha animation via expression engine: `alpha='min(1, (t-start)/fade_duration)'`, `enable='between(t, start, end)'`
- Contract tests use record-replay pattern (LRN-008) with existing `RecordingFFmpegExecutor`/`FakeFFmpegExecutor`
- Existing `escape_filter_text()` in Rust sanitize module handles text escaping

**Speed control (BL-041):**
- setpts builder: `PTS/factor` for video speed (0.25x-4.0x range)
- atempo builder: automatic chaining for factors >2x (FFmpeg limitation)
- Audio drop option for video-only speed changes
- Existing `validate_speed()` in Rust sanitize module handles range validation
- Frame-rate independent — PTS operates on timestamps, not frame numbers

See `comms/outbox/versions/design/v006/004-research/` for evidence.

## Risks

| Risk | Mitigation |
|------|------------|
| Contract tests require FFmpeg binary in CI | FFmpeg installed on all 9 CI matrix entries via AnimMouse/setup-ffmpeg@v1 — see `006-critical-thinking/risk-assessment.md` |
| Rust coverage threshold gap | Comprehensive unit tests and proptest for all new modules |
| Drop-frame timecode vs speed control | PTS is frame-rate independent; confirmed via DeepWiki research — see `006-critical-thinking/risk-assessment.md` |