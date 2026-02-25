# v012 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: rust-bindings-cleanup

**Path:** `comms/inbox/versions/execution/v012/01-rust-bindings-cleanup/`
**Goal:** Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. This reduces the public API surface from 11 unused Python-facing bindings to zero, lowers maintenance burden, and clarifies which Rust functions are intended for Python consumption.

**Features:**

- 001-execute-command-removal: Remove the dead execute_command() bridge function and its supporting code
- 002-v001-bindings-trim: Remove 5 unused v001 PyO3 bindings (TimeRange ops, sanitization) and associated tests
- 003-v006-bindings-trim: Remove 6 unused v006 PyO3 bindings (Expr, graph validation, composition) and associated parity tests
### Theme 02: workshop-and-docs-polish

**Path:** `comms/inbox/versions/execution/v012/02-workshop-and-docs-polish/`
**Goal:** Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation that shows misleading example values. These items address frontend and documentation gaps independently of Theme 01's binding cleanup work.

**Features:**

- 001-transition-gui: Wire transition effects into the Effect Workshop GUI via the existing backend endpoint
- 002-api-spec-corrections: Fix 5 documentation inconsistencies in API spec and manual for job status examples
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
