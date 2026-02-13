# Version Design: v006

## Description

**Effects Engine Foundation** — Build the Rust filter expression engine, graph validation, filter composition, text overlay builder, speed control, and effect discovery/application API endpoints.

v006 is the first version to tackle video effects. All prior versions (v001-v005) built the foundation (Rust core, database, API, testing, GUI). This version extends the Rust core with a filter expression DSL and composition system, then bridges them to the Python API layer with discovery and application endpoints. Covers Phase 2 milestones M2.1-M2.3.

## Design Artifacts

Full design analysis available at: `comms/outbox/versions/design/v006/`

- `001-environment/` — Environment context and project health
- `002-backlog/` — Backlog details, learnings summary, retrospective insights
- `003-impact-assessment/` — Codebase impact analysis
- `004-research/` — Research investigation (partial — see constraints)
- `005-logical-design/` — Original logical design, test strategy, risks
- `006-critical-thinking/` — Refined design, risk assessment, investigation log

## Constraints and Assumptions

- Independent of v005 — pure Rust + API work, no GUI changes
- All new Rust code follows coding standards: doc comments, no `unwrap()`, proper error handling
- PyO3 bindings added in the same feature (incremental binding rule)
- Python 3.10 compatibility required
- Rust coverage currently ~75% (target 90%) — v006 features must achieve >90% module-level coverage
- Research Task 004 was incomplete (timeout); gaps addressable during implementation

See `001-environment/version-context.md` for full context.

## Key Design Decisions

- **Expression function whitelist:** `{between, if, min, max}` + arithmetic + `{t, PTS, n}` — bounded by downstream consumer needs
- **Clip effects storage:** `effects_json TEXT` column via audit log JSON pattern; Rust Clip unchanged (LRN-011)
- **Effect registry:** Dictionary-based, following job handler registry pattern, injected via `create_app()` DI
- **Contract tests:** FFmpeg available on all 9 CI entries; existing record-replay infrastructure reused
- **Speed control:** `PTS/factor` is frame-rate independent; drop-frame timecode irrelevant

See `006-critical-thinking/risk-assessment.md` for rationale.

## Theme Overview

| # | Theme | Backlog Items | Features | Goal |
|---|-------|---------------|----------|------|
| 1 | filter-expression-infrastructure | BL-037, BL-038 | 2 | Type-safe expression engine and graph validation |
| 2 | filter-builders-and-composition | BL-039, BL-040, BL-041 | 3 | Drawtext, speed control, and composition system |
| 3 | effects-api-layer | BL-042, BL-043 | 3 | Discovery endpoint and text overlay application API |

See THEME_INDEX.md for detailed feature listing.
