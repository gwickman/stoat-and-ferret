# Exploration: design-v010-005-logical

## Summary

Synthesized Phase 1 outputs (001-environment, 002-backlog, 004-research) into a logical design proposal for v010 (Async Pipeline & Job Controls).

## What Was Produced

4 artifacts in `comms/outbox/versions/design/v010/005-logical-design/`:

1. **README.md** — Summary with theme overview, key decisions, dependencies, and risk table
2. **logical-design.md** — Complete logical design: 2 themes, 5 features, execution order, handler concurrency evaluation, and research sources adopted
3. **test-strategy.md** — Per-feature test requirements covering unit, integration, API, frontend, and cross-cutting concerns
4. **risks-and-unknowns.md** — 7 risks/unknowns with severity, description, investigation needed, and current assumptions (all unverified items labeled)

## Key Outcomes

- **2 themes, 5 features** — all 5 backlog items (BL-072, BL-073, BL-074, BL-077, BL-078) mapped
- **No deferrals** — all items are mandatory and assigned
- **0 new create_app() kwargs** — progress and cancellation are internal to AsyncioJobQueue
- **3 medium-severity risks** identified for Task 006 critical thinking review
- **No new MCP handlers** — handler concurrency section marked not applicable
