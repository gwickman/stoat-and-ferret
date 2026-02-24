# Exploration: design-v012-005-logical

## Summary

Synthesized Phase 1 findings (environment, backlog, research) into a coherent logical design proposal for v012 (API Surface & Bindings Cleanup). The proposal organizes 5 mandatory backlog items into 2 themes with 5 features, defines execution order based on dependency analysis, and identifies 6 risks for Task 006 review.

## Artifacts Produced

All outputs saved to `comms/outbox/versions/design/v012/005-logical-design/`:

| File | Description |
|------|-------------|
| `README.md` | Design summary with theme overview, key decisions, dependencies, and risks |
| `logical-design.md` | Complete logical design: 2 themes, 5 features with acceptance criteria, execution order, research sources, handler concurrency assessment |
| `test-strategy.md` | Test requirements per feature: ~66 tests removed, ~3 new test files, verification steps |
| `risks-and-unknowns.md` | 6 risks rated by severity with investigation needs and current assumptions |

## Key Findings

- All 5 backlog items mapped to features (no deferrals)
- BL-061 resolved as "remove" based on research evidence (zero callers, no render workflow)
- Theme 01 (bindings cleanup) and Theme 02 (workshop polish) are fully independent
- Net test impact: ~66 parity tests removed, ~3 new frontend test files created
- No new MCP handlers introduced — handler concurrency section noted as N/A
