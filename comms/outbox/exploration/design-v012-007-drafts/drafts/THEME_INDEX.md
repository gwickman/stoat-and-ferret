# Theme Index: v012

## Theme 01: rust-bindings-cleanup

Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. This reduces the public API surface, lowers maintenance burden, and clarifies which Rust functions are intended for Python consumption.

**Features:**

- 001-execute-command-removal: Remove the dead execute_command() bridge function and CommandExecutionError from the FFmpeg integration module
- 002-v001-bindings-trim: Remove 5 unused v001 PyO3 bindings (find_gaps, merge_ranges, total_coverage, validate_crf, validate_speed) and associated tests
- 003-v006-bindings-trim: Remove 6 unused v006 PyO3 bindings (Expr, validated_to_string, compose_chain, compose_branch, compose_merge) and associated parity tests

## Theme 02: workshop-and-docs-polish

Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation that shows misleading example values.

**Features:**

- 001-transition-gui: Wire transition effects into the Effect Workshop GUI via the existing backend endpoint with clip-pair selection
- 002-api-spec-corrections: Fix 5 documentation inconsistencies in API spec and manual for job status progress values and status enum
