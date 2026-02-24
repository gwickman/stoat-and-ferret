# Exploration: design-v012-004-research

Research and investigation for v012 (API Surface & Bindings Cleanup).

## Artifacts Produced

All saved to `comms/outbox/versions/design/v012/004-research/`:

1. **README.md** — Research questions, findings summary, recommendations, learning verifications
2. **codebase-patterns.md** — Detailed codebase investigation findings with file paths and line numbers for all 5 backlog items
3. **external-research.md** — Zustand paired selection patterns (DeepWiki), FFmpeg progress values, dead code removal patterns, session analytics insights
4. **evidence-log.md** — Concrete values with sources for all research parameters
5. **impact-analysis.md** — Dependencies, breaking changes, test infrastructure, documentation updates

No `persistence-analysis.md` — BL-066 stores transitions in existing Project model (already implemented in v007); no new persistent state introduced.

## Key Findings

- **BL-061**: Remove execute_command() — zero production callers, no render/export workflow exists
- **BL-066**: Frontend-only wiring — backend transition endpoint with adjacency validation is complete
- **BL-067**: Remove all 5 v001 bindings — zero production callers, Rust-internal validation covers sanitization
- **BL-068**: Remove all 6 v006 bindings — zero production callers, Rust uses functions internally without PyO3
- **BL-079**: Fix 5 API spec inconsistencies beyond the originally scoped progress null issue

## All Learnings Verified

8 learnings verified against current codebase — all VERIFIED, none STALE.
