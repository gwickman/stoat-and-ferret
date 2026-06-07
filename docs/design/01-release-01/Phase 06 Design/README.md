# Phase 6: Deployability & AI-Testability Design

Phase 6 completes the stoat-and-ferret production readiness story. It adds container deployment with multi-stage Docker builds, deployment safety (migration guards, rollback, feature flags), AI integration refinement (richer discovery, schema introspection), API testability infrastructure for external agents (system state snapshot, seed fixtures, WebSocket hardening), comprehensive documentation (OpenAPI, agent operator guides, prompt recipes), a final security and performance quality gate, and GUI polish (unified workspace layout, WCAG AA accessibility, E2E Playwright tests). The phase comprises 44 backlog items (18 S, 20 M, 6 L) across 7 themes, targeting versions v037–v043.

**Design status:** Initial design. All open questions resolved.

## Key Design Decisions

1. **Phase 5 residuals (BL-254/255/258) roll into v037 alongside M6.1 Container Deployment**: clearing residuals before starting new scope keeps the backlog clean; container work is independent and can proceed in parallel.
2. **System state snapshot (`GET /api/v1/system/state`) returns a denormalised read-only view**: avoids coupling agents to internal repository details; snapshot is a stable contract for external consumers.
3. **Test seed endpoint is config-guarded (`STOAT_TESTING_MODE=true`)**: prevents accidental fixture injection in production; endpoint returns 404 when guard is off.
4. **WebSocket replay uses a bounded event ring buffer (1000 events, 5-minute TTL)**: balances memory with reconnection reliability; agents reconnecting within TTL get catch-up delivery.
5. **GUI workspace uses CSS Grid with `react-resizable-panels`**: avoids heavy docking framework dependencies; CSS Grid is sufficient for the 3-panel presets (edit/review/render).
6. **Documentation-only milestones (M6.4, M6.8) are combined into one theme**: both produce Markdown/OpenAPI artifacts with no code changes; grouping them reduces version overhead.

## Document Inventory

Read in this order:

| # | File | Description |
|---|------|-------------|
| 1 | `01-deployment-data-models.md` | Pydantic models, Rust structs, and SQLite schema additions for deployment, testability, and workspace features |
| 2 | `02-rust-core-design.md` | Rust core additions: version info exposure, schema introspection helpers |
| 3 | `03-api-endpoints.md` | New and modified API endpoints: system state, seed, version, long-poll, feature flags |
| 4 | `04-observability-and-operations.md` | Deployment monitoring, synthetic checks, quality metrics dashboard, SLI tracking |
| 5 | `05-gui-integration.md` | Unified workspace layout, settings panel, accessibility, E2E GUI components |
| 6 | `06-test-strategy.md` | E2E Playwright tests, security review, performance benchmarks, load testing |
| 7 | `07-artifact-update-plan.md` | All new and modified files across the phase |
| 8 | `08-backlog-items.md` | 44 backlog items across 7 themes with sizing, acceptance criteria, and version mapping |

## Resolved Decisions

1. **Should v037 be Phase 5 cleanup or Phase 6 start?** Both — v037 clears three Phase 5 residuals (BL-254, BL-255, BL-258) alongside M6.1 container deployment. The residuals are small/medium items that don't warrant a standalone version.
2. **M6.7 persistence gap item already complete?** Yes — BL-251 (v036) already wired ThumbnailService and WaveformService to SQLite repositories. This sub-deliverable of M6.7 is excluded from Phase 6 backlog.
3. **MCP abstraction for AI agents?** Deferred to Phase 7+ per M6.8 decision criteria. Phase 6 provides REST+WebSocket patterns with documentation; MCP wrapping is a future concern.
4. **Feature flag implementation approach?** Environment-variable-based flags with a `FeatureFlags` singleton read at startup. No runtime toggle UI — flags are deployment-time configuration. This matches the project's existing `Settings` pattern.
5. **WebSocket replay vs. persistent event log?** Ring buffer replay (bounded, in-memory) chosen over persistent log. Sufficient for agent reconnection within a session; full event persistence is out of scope.

## Risks

| Risk | Mitigation |
|------|------------|
| Multi-stage Docker build complexity (Python + Rust + maturin) | Start with single-platform build; add cross-compilation in Phase 7 if needed |
| Security review may surface blocking issues late | Run security review (M6.5) as a mid-phase milestone, not final gate; fix-forward in later versions |
| WCAG AA compliance scope creep | Audit first, then fix only P1/P2 issues; defer P3 to Phase 7 |
| Agent operator docs may not match real agent behaviour | Validate docs against actual agent test workflow (M6.7 seed endpoint) before publishing |
| WebSocket ring buffer memory under load | Cap at 1000 events with 5-min TTL; monitor with Prometheus gauge; tune in production |

## Deviations from Phase 5 Design Pattern

1. **Minimal Rust core additions**: Phase 6 is primarily Python-side infrastructure and documentation. The Rust core design doc (02) is shorter than Phase 5's equivalent.
2. **Combined documentation theme**: M6.4 and M6.8 are merged into a single "Documentation & Agent Support" theme since both produce documentation artifacts with no code changes.
3. **Phase 5 residual items included**: Three open Phase 5 items (BL-254, BL-255, BL-258) are scheduled in v037 alongside Phase 6 work, noted explicitly in the backlog.
