# Logical Design — v005

v005 is structured as 4 themes with 13 features, covering all 10 backlog items (BL-003, BL-028 through BL-036). The design follows the "infrastructure first" principle (LRN-019): frontend scaffolding and WebSocket support land before GUI panels, and backend services (thumbnails, pagination) land before the library browser that consumes them.

## Theme Overview

| # | Theme | Goal | Features | Backlog Items |
|---|-------|------|----------|---------------|
| 01 | Frontend Foundation | Scaffold React/Vite project, configure FastAPI static serving, add WebSocket endpoint, update settings and docs | 3 | BL-003, BL-028, BL-029 |
| 02 | Backend Services | Add thumbnail generation pipeline and fix pagination total count | 2 | BL-032, BL-034 |
| 03 | GUI Components | Build application shell, dashboard, library browser, and project manager | 4 | BL-030, BL-031, BL-033, BL-035 |
| 04 | E2E Testing | Establish Playwright infrastructure with CI integration and write E2E + accessibility tests | 2 | BL-036 |

## Key Decisions

1. **React 18+ with TypeScript** selected over Svelte — larger ecosystem, design docs already React-aligned (JSX/hooks/Zustand in 08-gui-architecture.md), better virtual scrolling library options. See `comms/outbox/versions/design/v005/004-research/external-research.md` section 1.

2. **WebSocket grouped with frontend scaffolding** (Theme 01) — both modify `create_app()` and app lifespan. Bundling avoids repeated app factory changes.

3. **Backend services as separate theme** (Theme 02) — thumbnail pipeline and pagination fix are backend-only prerequisites for the library browser. Completing them before GUI work avoids blocking the library browser mid-theme.

4. **Sequential GUI component execution** (Theme 03) — shell first (provides layout frame), then dashboard (WebSocket consumer), library browser (depends on thumbnails + pagination), project manager (depends on shell only). Sequential ordering avoids merge conflicts in shared layout files.

5. **E2E testing as final theme** (Theme 04) — tests the integrated system after all components exist. Split into setup and test authoring for focused features.

## Dependencies

```
Theme 01 (Frontend Foundation)
    └──> Theme 02 (Backend Services) ──> only thumbnail pipeline needs settings from Theme 01
    └──> Theme 03 (GUI Components) ──> all panels need the shell and infrastructure
              └──> Theme 04 (E2E Testing) ──> tests need all GUI components
```

Theme 02's pagination fix (BL-034) is technically independent of Theme 01, but sequencing Theme 02 after Theme 01 maintains the infrastructure-first order and avoids parallel theme complexity.

## Risks and Unknowns

**High severity:**
- **R-1:** Framework selection (React vs Svelte) is a permanent technology choice. Research strongly favors React but no prototype validates this in the stoat-and-ferret context.

**Medium severity:**
- **R-2:** FastAPI `StaticFiles(html=True)` SPA routing may not handle all edge cases — custom handler documented as fallback
- **R-3:** WebSocket connection stability in long sessions — mitigated by heartbeat + reconnection logic
- **R-4:** Thumbnail generation could slow scan pipeline for large libraries — on-scan generation with lazy fallback option
- **UQ-2:** Virtual scrolling library choice deferred to BL-033 implementation

**Low severity:**
- R-5 (CI time), R-6 (virtual scrolling compat), UQ-1 (heartbeat interval), UQ-3 (thumbnail timing), UQ-4 (frontend coverage baseline)

Full analysis: `risks-and-unknowns.md`

## Detailed Documents

- `logical-design.md` — Full theme/feature breakdown with execution order and research sources
- `test-strategy.md` — Test requirements per feature
- `risks-and-unknowns.md` — All identified risks for Task 006 review
