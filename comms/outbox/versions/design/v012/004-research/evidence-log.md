# Evidence Log — v012

## execute_command Production Callers
- **Value**: 0 callers
- **Source**: Exhaustive grep of src/ for "execute_command"
- **Data**: Only occurrences are: definition (integration.py:43), export (__init__.py:10,29), tests (test_integration.py: 15 calls)
- **Rationale**: Confirms dead code status — supports "remove" decision

## ThumbnailService Direct Executor Usage
- **Value**: executor.run(args, timeout=30) called directly
- **Source**: src/stoat_ferret/api/services/thumbnail.py:69
- **Data**: ThumbnailService bypasses execute_command entirely, calling executor.run() with raw args
- **Rationale**: The only production FFmpeg workflow doesn't use the bridge function

## v001 Binding Production Callers
- **Value**: 0 callers for all 5 functions (find_gaps, merge_ranges, total_coverage, validate_crf, validate_speed)
- **Source**: Exhaustive grep of src/ (excluding tests/ and benchmarks/)
- **Data**: Functions only appear in __init__.py exports, stubs, test_pyo3_bindings.py, and bench_ranges.py
- **Rationale**: All 5 are safe to remove from PyO3 bindings without breaking production code

## v006 Binding Production Callers
- **Value**: 0 callers for Expr, validate, validated_to_string, compose_chain, compose_branch, compose_merge
- **Source**: Exhaustive grep of src/ (excluding tests/)
- **Data**: Expr imported in __init__.py but never used in production. DrawtextBuilder and DuckingPattern use Rust-internal Expr/compose — not the PyO3 wrappers
- **Rationale**: PyO3 wrappers are redundant; Rust code uses the functions internally without Python bindings

## Rust Internal CRF Validation
- **Value**: FFmpegCommand.validate() checks crf > 51 at command.rs:582-586
- **Source**: rust/stoat_ferret_core/src/ffmpeg/command.rs
- **Data**: `if let Some(crf) = output.crf { if crf > 51 { return Err(CommandError::InvalidCrf(crf)); } }`
- **Rationale**: Rust-internal validation covers CRF range check — PyO3 wrapper validate_crf is redundant

## Rust Internal Speed Validation
- **Value**: SpeedControl.new() calls sanitize::validate_speed() at speed.rs:116-117
- **Source**: rust/stoat_ferret_core/src/ffmpeg/speed.rs
- **Data**: `sanitize::validate_speed(factor).map_err(|e| e.to_string())?` — validates 0.25-4.0 range
- **Rationale**: Rust-internal validation covers speed range check — PyO3 wrapper validate_speed is redundant

## Transition Endpoint Adjacency Validation
- **Value**: Strict adjacency check: target_idx == source_idx + 1
- **Source**: src/stoat_ferret/api/routers/effects.py:556-566
- **Data**: Returns 400 NOT_ADJACENT if clips not consecutive in timeline order
- **Rationale**: Backend adjacency validation is complete — GUI only needs to enforce UX convenience, not correctness

## Progress Value Range
- **Value**: 0.0-1.0 (normalized float)
- **Source**: src/stoat_ferret/jobs/queue.py:36-52, src/stoat_ferret/api/services/scan.py:214-215
- **Data**: `progress_callback(processed / total_files)` produces 0.0-1.0; JobResult.progress documented as "Progress value 0.0-1.0"
- **Rationale**: API manual incorrectly says "0-100" — must be corrected to match code

## Parity Test Counts
- **Value**: ~22 tests for v001 bindings, ~31 tests for v006 bindings
- **Source**: tests/test_pyo3_bindings.py
- **Data**: TestRangeListOperations (15 tests), TestSanitization (4 for crf/speed), TestExpr (16), composition (~15)
- **Rationale**: These tests become invalid when bindings are removed — plan removal as explicit sub-tasks

## Effect Workshop Schema-Driven Pattern
- **Value**: 11 parameter_schema occurrences in definitions.py
- **Source**: src/stoat_ferret/effects/definitions.py, grep count
- **Data**: Each EffectDefinition includes a JSON Schema dict with properties, required fields, defaults, min/max bounds
- **Rationale**: BL-066 transition GUI should follow this established pattern

## Session Duration Baseline
- **Value**: Exploration sessions average 88-325 seconds
- **Source**: query_cli_sessions, analytics mode, session_list, last 60 days
- **Data**: 20 sessions analyzed; design exploration sessions range 88-325s with 21-45 tool calls
- **Rationale**: Source: query_cli_sessions. v012 features are well-scoped; audit-and-trim tasks should be on the faster end
