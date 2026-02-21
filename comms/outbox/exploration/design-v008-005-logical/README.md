# Exploration: design-v008-005-logical

## Task

Synthesize Phase 1 outputs (Tasks 001-004) into a logical design proposal for v008 "Startup Integrity & CI Stability."

## What Was Produced

All artifacts saved to `comms/outbox/versions/design/v008/005-logical-design/`:

1. **logical-design.md** — Complete design proposal with 2 themes, 4 features, execution order, feature details, research sources adopted, and handler concurrency decisions.

2. **test-strategy.md** — Per-feature test requirements: ~16 new tests (9 unit + 7 system/integration), 3 existing test file modifications (helper consolidation), 1 E2E modification (timeout parameter).

3. **risks-and-unknowns.md** — 7 risks identified for Task 006 critical review (3 medium severity, 4 low severity). Key risks: logging activation test impact, E2E count-based AC validation, configure_logging() guard placement.

4. **README.md** — Summary with theme overview, key decisions, dependencies, and risk table.

## Key Decisions

- 2 themes: 01-application-startup-wiring (3 features), 02-ci-stability (1 feature)
- All 4 backlog items mapped — no deferrals
- Execution: database → logging → settings → E2E fix
- create_tables() over Alembic (simpler, with documented upgrade path)
- No new MCP handlers — handler concurrency section marked N/A

## Phase 1 Sources Consumed

- `comms/outbox/versions/design/v008/001-environment/` (3 files)
- `comms/outbox/versions/design/v008/002-backlog/` (4 files)
- `comms/outbox/versions/design/v008/004-research/` (5 files)
