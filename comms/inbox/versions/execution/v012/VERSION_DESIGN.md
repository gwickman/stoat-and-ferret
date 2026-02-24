# v012 Version Design

## Overview

**Version:** v012
**Title:** API Surface & Bindings Cleanup
**Themes:** 2

## Backlog Items

- [BL-061](docs/auto-dev/BACKLOG.md#bl-061)
- [BL-066](docs/auto-dev/BACKLOG.md#bl-066)
- [BL-067](docs/auto-dev/BACKLOG.md#bl-067)
- [BL-068](docs/auto-dev/BACKLOG.md#bl-068)
- [BL-079](docs/auto-dev/BACKLOG.md#bl-079)

## Design Context

### Rationale

Reduce technical debt in the Rust-Python boundary by removing dead code, wire remaining GUI gaps, and correct documentation inconsistencies.

### Constraints

- v011 must be deployed before v012 starts (confirmed complete)
- All 5 backlog items are P2 or P3 — no P1 urgency
- Phase 3 Composition Engine is deferred — removed bindings must have documented re-add triggers

### Assumptions

- Re-adding PyO3 wrappers is mechanical (~5-10 lines per binding)
- Rust-internal usage of removed binding functions is unaffected
- Backend transition endpoint is functional and tested

### Deferred Items

- BL-069 — C4 documentation update (deferred, not stoat-and-ferret code change)

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-rust-bindings-cleanup | Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. | 3 |
| 2 | 02-workshop-and-docs-polish | Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation inconsistencies. | 2 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (rust-bindings-cleanup): Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers.
- [ ] Theme 02 (workshop-and-docs-polish): Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation inconsistencies.
