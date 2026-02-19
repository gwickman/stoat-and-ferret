# Theme 02: effect-registry-api Retrospective

## Summary

Refactored the effect registry from if/elif dispatch to builder-protocol dispatch with `build_fn`, added JSON schema validation via `jsonschema`, created the `POST /effects/transition` endpoint with clip adjacency validation, and updated architecture and API specification docs to reflect all v007 changes. All 3 features shipped with 26/26 acceptance criteria passing and all quality gates green.

## Deliverables

| Feature | Status | Acceptance | Quality Gates | Notes |
|---------|--------|------------|---------------|-------|
| 001-effect-registry-refactor | Complete | 14/14 | ruff, mypy, pytest — all pass | Builder dispatch, JSON schema validation, 9 effects registered, Prometheus counter |
| 002-transition-api-endpoint | Complete | 5/5 | ruff, mypy, pytest — all pass | POST /effects/transition with adjacency validation, persistent storage |
| 003-architecture-documentation | Complete | 7/7 | ruff, mypy, pytest — all pass | Updated 02-architecture.md and 05-api-specification.md |

## Metrics

- **Commits:** 3 (`338e1ad`, `a059cf5`, `53fb101`)
- **Source lines changed:** ~1,100 across production code, ~825 across test code, ~390 across documentation
- **New tests added:** 32 (18 registry + 14 transition)
- **Total pytest suite:** 854 passed, 20 skipped at theme completion
- **Coverage:** 92.24% (threshold: 80%)
- **New dependency:** `jsonschema` (+ `types-jsonschema` for mypy)

## Key Decisions

### Builder dispatch via `build_fn` field on EffectDefinition
**Context:** The effects router used a monolithic `_build_filter_string()` with if/elif branches for each effect type. Adding new effects required modifying the router.
**Choice:** Added a `build_fn: Callable[[dict[str, Any]], str]` field to `EffectDefinition` so each effect carries its own build function. The router calls `definition.build_fn(parameters)` directly.
**Outcome:** Open/closed principle — new effects are added by registering a definition, not by modifying dispatch logic. All 9 effects now self-contained.

### JSON schema validation via Draft7Validator
**Context:** Parameter validation was implicit in the build functions, producing unhelpful errors on bad input.
**Choice:** Each `EffectDefinition` includes a JSON schema; `registry.validate()` uses `jsonschema.Draft7Validator` to produce structured error messages before dispatch.
**Outcome:** Clear, actionable validation errors for missing fields, type mismatches, and constraint violations. Added `jsonschema` as a runtime dependency.

### Clip adjacency validation for transitions
**Context:** Transitions between non-adjacent clips are semantically invalid and would produce broken FFmpeg filter graphs.
**Choice:** The transition endpoint validates that `from_clip` and `to_clip` are adjacent in the project timeline, returning specific error codes (`SAME_CLIP`, `EMPTY_TIMELINE`, `NOT_ADJACENT`).
**Outcome:** Prevents invalid filter generation at the API layer with clear error messages.

### Persistent transition storage on Project model
**Context:** Applied transitions need to survive server restarts for project consistency.
**Choice:** Added `transitions` field to the `Project` dataclass and `transitions_json` column to the SQLite schema, serializing as JSON.
**Outcome:** Transitions round-trip through the database correctly. Repository parity tests updated to cover the new column.

## Learnings

### What Went Well
- Builder dispatch pattern cleanly replaced the if/elif monolith — the router shrank while gaining functionality
- JSON schema validation catches parameter errors before they reach Rust builders, producing better error messages than letting PyO3 type coercion fail
- Parity tests (comparing new dispatch output against hardcoded expected strings) caught regressions during the refactor
- Feature handoff documents between 001 and 002 enabled the transition endpoint to build directly on the registry dispatch without rework
- Documentation feature (003) was efficient because it followed immediately after the implementation features while context was fresh

### What Could Improve
- The `definitions.py` file grew significantly (~576 lines added) with 7 new build functions and their schema definitions — could benefit from splitting per-effect-domain modules (audio, video, transition) in a future refactor
- No quality-gaps.md files were generated, which is positive but also means there's no structured technical debt tracking from the automated pipeline for this theme

## Technical Debt

- **Large definitions module:** `definitions.py` contains build functions and schemas for all 9 effects in a single file. As more effects are added, consider splitting into domain-specific modules (`audio_definitions.py`, `transition_definitions.py`, etc.)
- **Transition storage as JSON column:** `transitions_json` stores an array of dicts as a JSON string in SQLite. This works at current scale but would need normalization if transitions gain complex query requirements.

## Recommendations

1. **For future registry extensions:** Follow the pattern established here — add a build function, define the JSON schema, register in `create_default_registry()`, and add parity tests. The pattern is well-proven across 9 effects now.
2. **Schema-first validation:** The JSON schema approach works well for effects with simple parameter types. If effects need cross-field validation (e.g., "end_time must be after start_time"), consider extending `validate()` with custom validators beyond what JSON schema provides.
3. **Definitions module size:** Monitor the size of `definitions.py` — if a 10th+ effect type is added, split into domain modules to keep files navigable.
