# Exploration: design-v011-005-logical

Completed Task 005 (Logical Design Proposal) for v011. Synthesized findings from Tasks 001-004 into a coherent design with theme groupings, feature breakdowns, test strategy, and risk inventory.

## What Was Produced

All artifacts saved to `comms/outbox/versions/design/v011/005-logical-design/`:

- **README.md** — Summary of proposed structure, key decisions, dependencies, and risk overview
- **logical-design.md** — Complete logical design: 2 themes, 5 features, execution order, research sources adopted, handler concurrency decisions
- **test-strategy.md** — Test requirements per feature: 5 pytest tests, 18 Vitest tests, 6 manual checks, 4 new test files, 2 existing test files affected
- **risks-and-unknowns.md** — 7 identified risks (1 high, 3 medium, 3 low) for Task 006 critical review

## Key Design Decisions

1. Backend-assisted directory listing for browse button (browser API lacks cross-browser support)
2. Independent Zustand store pattern for clip state management
3. Dropped `label` field from clip form (not in backend schema)
4. All 5 backlog items mapped to features — zero deferrals
5. Themes executable in parallel with documented intra-theme ordering constraints
