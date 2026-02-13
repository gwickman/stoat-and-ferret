# v006 Version Design

## Overview

**Version:** v006
**Title:** Effects Engine Foundation — Build the Rust filter expression engine, graph validation, filter composition, text overlay builder, speed control, and effect discovery/application API endpoints.
**Themes:** 3

## Backlog Items

- [BL-037](docs/auto-dev/BACKLOG.md#bl-037)
- [BL-038](docs/auto-dev/BACKLOG.md#bl-038)
- [BL-039](docs/auto-dev/BACKLOG.md#bl-039)
- [BL-040](docs/auto-dev/BACKLOG.md#bl-040)
- [BL-041](docs/auto-dev/BACKLOG.md#bl-041)
- [BL-042](docs/auto-dev/BACKLOG.md#bl-042)
- [BL-043](docs/auto-dev/BACKLOG.md#bl-043)

## Design Context

### Rationale

v006 is the first version to tackle video effects. All prior versions (v001-v005) built the foundation (Rust core, database, API, testing, GUI). This version extends the Rust core with a filter expression DSL and composition system, then bridges them to the Python API layer with discovery and application endpoints. Covers Phase 2 milestones M2.1-M2.3.

### Constraints

- Independent of v005 — pure Rust + API work, no GUI changes
- All new Rust code must have doc comments, no unwrap() in library code
- PyO3 bindings added in the same feature (incremental binding rule)
- py_ prefix convention for binding methods with #[pyo3(name = ...)] clean names
- Python 3.10 compatibility — use asyncio.TimeoutError not builtins.TimeoutError
- Python coverage 80% minimum, Rust coverage 90% minimum target
- Rust coverage currently at ~75% from v004 deferral

### Assumptions

- Research gaps (Task 004 incomplete) are addressable during implementation
- Effects stored as JSON list on clip model, serialized to DB as TEXT column
- Rust Clip type unchanged — Python owns effect storage, Rust owns filter generation
- Existing CI FFmpeg setup sufficient for contract tests
- setpts PTS/factor is frame-rate independent — drop-frame timecode irrelevant

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-filter-expression-infrastructure | Build the foundational Rust infrastructure — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization. | 2 |
| 2 | 02-filter-builders-and-composition | Build the concrete filter builders (drawtext, speed control) and the composition system for chaining, branching, and merging filter graphs. | 3 |
| 3 | 03-effects-api-layer | Bridge the Rust effects engine to the Python API layer with discovery and application endpoints. | 3 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (filter-expression-infrastructure): Build the foundational Rust infrastructure — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization.
- [ ] Theme 02 (filter-builders-and-composition): Build the concrete filter builders (drawtext, speed control) and the composition system for chaining, branching, and merging filter graphs.
- [ ] Theme 03 (effects-api-layer): Bridge the Rust effects engine to the Python API layer with discovery and application endpoints.
