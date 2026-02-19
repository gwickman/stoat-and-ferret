---
status: complete
acceptance_passed: 7
acceptance_total: 7
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-architecture-documentation

## Summary

Updated `docs/design/02-architecture.md` and `docs/design/05-api-specification.md` to reflect the registry refactoring (T02-F001) and transition endpoint (T02-F002) changes from v007.

## Changes Made

### docs/design/02-architecture.md

1. **Rust module structure**: Added `audio.rs` and `transitions.rs` to the ffmpeg submodule listing and directory structure.
2. **Rust core responsibilities**: Added audio mixing and transition filter builders to the responsibility list.
3. **Effects Service section**: Rewritten to describe registry-based dispatch via `build_fn`, `validate()` method using Draft7Validator, and Prometheus metrics counters. Updated from 2 to 9 registered effects.
4. **PyO3 bindings section**: Added `VolumeBuilder`, `AfadeBuilder`, `AmixBuilder`, `DuckingPattern`, `TransitionType`, `FadeBuilder`, `XfadeBuilder`, `AcrossfadeBuilder`.
5. **Pure functions list**: Added audio and transition builder types.
6. **Metrics section**: Updated to reflect actual implemented Prometheus metrics (`stoat_ferret_effect_applications_total`, `stoat_ferret_transition_applications_total`, `http_requests_total`, etc.).
7. **Effect Definition Schema**: Added `build_fn` field to `EffectDefinition` dataclass, updated registered effects table from 2 to 9 entries.
8. **Python API examples**: Added v007 audio/transition builder examples.
9. **Audio/Transitions module docs**: Added full documentation sections with Rust code examples for both new modules.

### docs/design/05-api-specification.md

1. **POST /effects/transition endpoint**: Fully documented with request/response schemas, adjacency validation rules, and all error codes.
2. **Effect discovery response**: Expanded from 2 effects to all 9 registered effects with full parameter schemas, AI hints, and filter previews.
3. **Error codes table**: Added `SAME_CLIP`, `EMPTY_TIMELINE`, `NOT_ADJACENT` transition-specific error codes.
4. **AI integration example**: Added transition example showing how an AI agent would create a dissolve transition between clips.
5. **Registry dispatch pattern**: Documented in the discovery endpoint description (build_fn dispatch to Rust builders).

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001.1 | Rust module additions documented (audio.rs, transitions.rs) | Pass |
| FR-001.2 | Effects Service section rewritten for registry-based dispatch | Pass |
| FR-001.3 | PyO3 bindings updated with audio/transition builder classes | Pass |
| FR-001.4 | Registered effects list updated (9 effect types) | Pass |
| FR-001.5 | Prometheus metrics updated with effect_applications_total | Pass |
| FR-002.1 | POST /effects/transition documented with schemas | Pass |
| FR-002.2 | Effect discovery response updated with new effect types | Pass |

## Quality Gates

- ruff check: pass (all checks passed)
- ruff format: pass (111 files formatted)
- mypy: pass (no issues in 49 source files)
- pytest: pass (854 passed, 20 skipped, 92.24% coverage)
