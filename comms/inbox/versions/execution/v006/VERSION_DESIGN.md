# v006 Version Design

## Overview

**Version:** v006
**Title:** Effects Engine Foundation — Build a greenfield Rust filter expression engine with graph validation, composition system, text overlay builder, speed control builders, effect discovery API, and clip effect application endpoint.
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

First version to enter Phase 2 (Effects & Composition), building on the complete Phase 1 foundation (v001-v005). Maps to roadmap milestones M2.1-M2.3.

### Constraints

- Independence from v005 — v006 is pure Rust + API work with no dependency on v005's GUI components
- PyO3 incremental binding rule — all new Rust types must include PyO3 bindings in the same feature
- Existing FFmpeg module is the integration point for new filter builders
- CI Rust coverage stays at 75% threshold — new code targets >90% individually
- No new external Rust dependencies (no petgraph, no proptest-derive)

### Assumptions

- Phase 1 foundation (v001-v005) is complete and stable
- FFmpeg 5.0+ is available in all environments
- Greenfield Rust work — no existing filter expression module to extend
- Dev databases are ephemeral — no migration framework needed for schema changes

### Deferred Items

- Rust coverage ratchet from 75% to 90% (separate post-v006 effort)
- Per-side boxborderw syntax (FFmpeg 5.0+ only)
- C4 architecture documentation update (tracked as BL-018)

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-filter-engine | Build the foundational Rust filter infrastructure — expression type system, filter graph validation, and composition API. | 3 |
| 2 | 02-filter-builders | Implement concrete filter builders for text overlay and speed control using the expression engine from Theme 01. | 2 |
| 3 | 03-effects-api | Create the Python-side effect registry, discovery API endpoint, clip effect application endpoint, and update architecture documentation. | 3 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (filter-engine): Build the foundational Rust filter infrastructure — expression type system, filter graph validation, and composition API.
- [ ] Theme 02 (filter-builders): Implement concrete filter builders for text overlay and speed control using the expression engine from Theme 01.
- [ ] Theme 03 (effects-api): Create the Python-side effect registry, discovery API endpoint, clip effect application endpoint, and update architecture documentation.
