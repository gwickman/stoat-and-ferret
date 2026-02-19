# Theme 01: rust-filter-builders Retrospective

## Summary

Delivered Rust filter builders for two new effect domains — audio mixing and video transitions — extending the proven v006 builder pattern (LRN-028) to cover the remaining FFmpeg effect types needed by the effect registry and GUI. Both features shipped with all acceptance criteria passing and all quality gates green across Rust and Python.

## Deliverables

| Feature | Status | Acceptance | Quality Gates | Notes |
|---------|--------|------------|---------------|-------|
| 001-audio-mixing-builders | Complete | 12/12 | ruff, mypy, pytest, clippy, cargo_test — all pass | VolumeBuilder, AfadeBuilder, AmixBuilder, DuckingPattern |
| 002-transition-filter-builders | Complete | 30/30 | ruff, mypy, pytest — all pass | FadeBuilder, XfadeBuilder, AcrossfadeBuilder, TransitionType enum |

## Metrics

- **Lines added:** ~4,750 across both features
- **Rust source:** `audio.rs` (1,282 lines), `transitions.rs` (1,177 lines)
- **Rust unit tests:** 89 (54 audio + 35 transition)
- **Python parity tests:** 88 (42 audio + 46 transition)
- **Total pytest suite:** 821 passed, 20 skipped after theme completion
- **Coverage:** 92.71% (at feature 001 completion)
- **Commits:** 2 (`9a35226`, `6991f38`)

## Key Decisions

### Reusing FadeCurve for AcrossfadeBuilder
**Context:** AcrossfadeBuilder needs curve parameters identical to AfadeBuilder's FadeCurve enum.
**Choice:** Reused the FadeCurve enum from the audio module rather than duplicating it.
**Outcome:** Clean cross-module reuse, single source of truth for FFmpeg curve types.

### 59 vs 64 TransitionType variants
**Context:** Requirements specified 64 xfade variants based on early research, but actual FFmpeg source has 59 (58 built-in + custom).
**Choice:** Implemented all 59 actual FFmpeg variants rather than padding to match the spec number.
**Outcome:** Correct enum that matches FFmpeg reality. Documented the deviation in the completion report.

### Manual stub entries for TransitionType enum
**Context:** `pyo3_stub_gen`'s `#[gen_stub_pyclass]` macro does not support enums.
**Choice:** Manually added TransitionType to both `_core.pyi` stub files.
**Outcome:** Full type-checking support. This is a known pattern — the same approach was used for FadeCurve.

## Learnings

### What Went Well
- The v006 builder template pattern (LRN-028) transferred cleanly to both audio and transition domains with minimal adaptation
- Fluent method chaining pattern provides consistent ergonomics across all 7 new builder classes
- Parallel Rust unit tests + Python parity tests caught integration issues early
- DuckingPattern's use of FilterGraph composition API (`compose_branch`, `compose_merge`, `compose_chain`) validated the graph API design from earlier versions

### What Could Improve
- `pyo3_stub_gen` enum limitation requires manual stub maintenance — this is accumulating as more enums are added (FadeCurve, TransitionType)
- Requirements research phase over-counted xfade variants (64 vs actual 59) — could validate counts against FFmpeg source during design

## Technical Debt

No quality-gaps.md files were generated for either feature, indicating clean implementations. Minor items to note:

- **Manual enum stubs:** TransitionType and FadeCurve require hand-maintained entries in both `_core.pyi` files. As more enums are added, consider a stub generation script that handles enums.
- **Stub file duplication:** Stubs exist in both `src/stoat_ferret_core/_core.pyi` and `stubs/stoat_ferret_core/_core.pyi` — both must be kept in sync manually.

## Recommendations

1. **For future builder themes:** Continue following the v006 template pattern — it scales well. Start from an existing builder as a template.
2. **Enum stub tooling:** If a third enum type is needed, invest in automating enum stub generation to reduce manual maintenance burden.
3. **Requirements validation:** Cross-check numeric claims in requirements (e.g., "64 variants") against upstream source documentation during the design phase to avoid spec-vs-reality mismatches during implementation.
