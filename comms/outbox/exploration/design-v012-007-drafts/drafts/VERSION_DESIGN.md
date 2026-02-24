# Version Design: v012

## Description

**v012 — API Surface & Bindings Cleanup**

Reduce technical debt in the Rust-Python boundary by removing dead code (execute_command and 11 unused PyO3 bindings), wire the transition API into the Effect Workshop GUI, and correct documentation inconsistencies in API spec examples.

5 backlog items across 2 themes and 5 features.

## Design Artifacts

Full design analysis available at: `comms/outbox/versions/design/v012/`

- `001-environment/` — version context, dependency confirmation
- `002-backlog/` — backlog item details, retrospective insights
- `004-research/` — codebase patterns, evidence log, external research
- `005-logical-design/` — original logical design, test strategy
- `006-critical-thinking/` — refined design, risk assessment, investigation log

## Constraints and Assumptions

- v011 deployed and confirmed complete (2026-02-24)
- All 5 backlog items are P2/P3 — no P1 urgency
- Phase 3 Composition Engine is deferred — removed bindings documented with re-add triggers
- Re-adding PyO3 wrappers is mechanical (~5-10 lines per binding)
- Backend transition endpoint already exists and is functional

See `001-environment/version-context.md` for full context.

## Key Design Decisions

- **execute_command removal** (not wiring): Zero production callers confirmed; ThumbnailService calls executor.run() directly
- **Extended ClipSelector** (not separate ClipPairSelector): Pair-mode props on existing component follow KISS/DRY, avoids duplicating ~45 lines of clip rendering logic
- **Post-removal stub grep verification**: Added explicit manual stub verification step to binding trim features to address one-way verification gap in verify_stubs.py
- **Full parity test removal**: Dead tests removed entirely (not commented/archived) — recoverable from git history

See `006-critical-thinking/risk-assessment.md` for rationale.

## Theme Overview

| # | Theme | Goal | Features | Backlog Items |
|---|-------|------|----------|---------------|
| 1 | rust-bindings-cleanup | Remove dead code and unused PyO3 bindings | 3 | BL-061, BL-067, BL-068 |
| 2 | workshop-and-docs-polish | Wire transition GUI and fix API spec docs | 2 | BL-066, BL-079 |

See `THEME_INDEX.md` for feature-level details.
