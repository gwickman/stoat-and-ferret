# Theme: quality-validation

## Goal

Validate the complete effect workshop through end-to-end testing with accessibility compliance, and update API specification documentation to reflect all new endpoints added in v007.

## Design Artifacts

See `comms/outbox/versions/design/v007/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | e2e-effect-workshop-tests | BL-052 | E2E tests covering catalog browse, parameter config, preview, apply/edit/remove effects, and WCAG AA accessibility |
| 002 | api-specification-update | — | Update OpenAPI spec and docs/design/05-api-specification.md with transition, preview, and CRUD endpoints |

## Dependencies

- T03 complete: all GUI components must be functional for E2E testing
- T02 complete: all API endpoints must exist for API specification update
- Existing Playwright + axe-core E2E infrastructure from v005
- Existing SPA navigation workaround (LRN-023): tests navigate via client-side clicks

## Technical Approach

1. **E2E tests** (F001): Playwright tests covering the full effect workshop workflow — browse catalog, configure parameters, verify preview, apply/edit/remove effects. Axe-core accessibility scans for WCAG AA compliance on all form components. Navigate via client-side routing (SPA fallback still deferred).

2. **API spec update** (F002): Update `docs/design/05-api-specification.md` with all new endpoints: POST /effects/transition, effect preview, PATCH/DELETE effect CRUD. Update `docs/design/01-roadmap.md` and `docs/design/08-gui-architecture.md` milestone checkboxes. Document SPA fallback as known limitation.

See `comms/outbox/versions/design/v007/004-research/codebase-patterns.md` for E2E test patterns.

## Risks

| Risk | Mitigation |
|------|------------|
| SPA fallback routing still missing | E2E tests navigate via client-side routing. Document as known limitation. See 006-critical-thinking/risk-assessment.md |