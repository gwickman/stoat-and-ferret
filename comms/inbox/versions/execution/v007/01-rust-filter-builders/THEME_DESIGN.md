# Theme: rust-filter-builders

## Goal

Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern (LRN-028) to two new effect domains. These builders provide the type-safe foundation that the effect registry and GUI consume.

## Design Artifacts

See `comms/outbox/versions/design/v007/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | audio-mixing-builders | BL-044 | Build AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern in Rust with PyO3 bindings |
| 002 | transition-filter-builders | BL-045 | Build FadeBuilder, XfadeBuilder with TransitionType enum and AcrossfadeBuilder in Rust with PyO3 bindings |

## Dependencies

- v006 complete: filter expression engine, graph validation, builder pattern template (DrawtextBuilder, SpeedControl)
- BL-037 expression engine (delivered in v006) for fade curve support
- Existing FilterChain multi-input support for two-input filters (xfade, acrossfade, sidechaincompress)

## Technical Approach

Follow the proven builder template from v006 (LRN-028): `#[pyclass]` struct with typed fields, `#[new]` constructor with validation, fluent `PyRefMut` chaining methods, `.build()` returning `Filter`, PyO3 bindings with `#[pyo3(name = "...")]`, and `#[gen_stub_pyclass]` for stubs.

- Audio builders (F001): AmixBuilder (multi-input), VolumeBuilder, AfadeBuilder (single-input), DuckingPattern (composite using FilterGraph composition API)
- Transition builders (F002): FadeBuilder (single-input), XfadeBuilder (two-input via `FilterChain.input()`), AcrossfadeBuilder (two-input)

See `comms/outbox/versions/design/v007/004-research/codebase-patterns.md` for builder template details and `004-research/external-research.md` for FFmpeg filter parameters.

## Risks

| Risk | Mitigation |
|------|------------|
| Two-input filter pattern untested in builder template | Resolved: FilterChain multi-input already proven through concat tests. See 006-critical-thinking/risk-assessment.md |
| Audio ducking composite pattern complexity | Resolved: DuckingPattern uses FilterGraph composition API (compose_branch + compose_chain + compose_merge). See 006-critical-thinking/risk-assessment.md |
| Rust coverage target gap (75% vs 90%) | ~54 new unit tests expected to improve coverage. Track before/after T01. See 006-critical-thinking/risk-assessment.md |