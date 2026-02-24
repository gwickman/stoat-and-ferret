# v011 Version Design

## Overview

**Version:** v011
**Title:** GUI Usability & Developer Experience — Close the biggest GUI interaction gaps and improve onboarding/process documentation.
**Themes:** 2

## Backlog Items

- [BL-019](docs/auto-dev/BACKLOG.md#bl-019)
- [BL-070](docs/auto-dev/BACKLOG.md#bl-070)
- [BL-071](docs/auto-dev/BACKLOG.md#bl-071)
- [BL-075](docs/auto-dev/BACKLOG.md#bl-075)
- [BL-076](docs/auto-dev/BACKLOG.md#bl-076)

## Design Context

### Rationale

v010 delivered async ffprobe, progress reporting, and job cancellation. v011 addresses the remaining GUI gaps (clip CRUD wiring, directory browsing) and developer onboarding friction (.env.example, Windows guidance, impact assessment checks).

### Constraints

- v010 must be deployed (completed 2026-02-23)
- No inter-theme dependencies — themes can execute in parallel
- Backend clip CRUD endpoints already exist — BL-075 is frontend-only
- showDirectoryPicker() not viable — Firefox/Safari lack support
- No label field in clip schema — BL-075 AC3 reference is an error

### Assumptions

- Empty allowed_scan_roots means all directories permitted (confirmed by LRN-017)
- Simple <select> dropdown sufficient for video selection in clip form
- Sequential await with isLoading guard sufficient for race condition mitigation
- IMPACT_ASSESSMENT.md markdown format consumable by auto-dev Task 003 agent

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-scan-and-clip-ux | Deliver the missing GUI interaction layer for media scanning and clip management. | 2 |
| 2 | 02-developer-onboarding | Reduce onboarding friction and establish project-specific design-time quality checks. | 3 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (scan-and-clip-ux): Deliver the missing GUI interaction layer for media scanning and clip management.
- [ ] Theme 02 (developer-onboarding): Reduce onboarding friction and establish project-specific design-time quality checks.
