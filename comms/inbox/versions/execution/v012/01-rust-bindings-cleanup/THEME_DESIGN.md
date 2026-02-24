# Theme: rust-bindings-cleanup

## Goal

Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. This reduces the public API surface from 11 unused Python-facing bindings to zero, lowers maintenance burden, and clarifies which Rust functions are intended for Python consumption.

## Design Artifacts

See `comms/outbox/versions/design/v012/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | execute-command-removal | BL-061 | Remove the dead execute_command() bridge function and CommandExecutionError from FFmpeg integration |
| 002 | v001-bindings-trim | BL-067 | Remove 5 unused v001 PyO3 bindings (TimeRange ops, sanitization) and associated tests |
| 003 | v006-bindings-trim | BL-068 | Remove 6 unused v006 PyO3 bindings (Expr, graph validation, composition) and associated parity tests |

## Dependencies

- No external dependencies — all features modify existing code
- Feature 001 must complete before Features 002/003 (execute_command decision finalizes what counts as "unused")
- Features 002 and 003 can execute in parallel after Feature 001

## Technical Approach

Dead code removal with documented upgrade triggers (LRN-029). Each feature removes Python-facing bindings while preserving Rust-internal implementations. Post-removal verification includes stub regeneration, grep verification of manual stubs, and full test suite execution.

See `comms/outbox/versions/design/v012/004-research/` for evidence of zero production callers.

## Risks

| Risk | Mitigation |
|------|------------|
| Accidental removal of bindings needed by Phase 3 | Investigation confirmed none needed; re-add triggers documented. See 006-critical-thinking/risk-assessment.md |
| Parity test removal reduces equivalence confidence | ~120+ active parity tests remain; removed tests recoverable from git history |
| Stub regeneration may require manual fixups | Post-removal grep verification added to acceptance criteria |
| Edit tool non-unique match in large test files | Use class-level deletion rather than method-by-method editing |