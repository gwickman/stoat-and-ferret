# Theme 04: quality-validation Retrospective

## Summary

Validated the complete v007 Effect Workshop through end-to-end Playwright tests with WCAG AA accessibility compliance, and updated all three design documents (API specification, roadmap, GUI architecture) to reflect the final state of the implementation. Both features shipped with 14/14 acceptance criteria passing and all quality gates green.

## Deliverables

| Feature | Status | Acceptance | Quality Gates | Notes |
|---------|--------|------------|---------------|-------|
| 001-e2e-effect-workshop-tests | Complete | 5/5 | ruff, mypy, pytest, tsc, vitest — all pass | Catalog browse, parameter config, apply/edit/remove, keyboard nav, axe-core a11y |
| 002-api-specification-update | Complete | 9/9 | ruff, mypy, pytest — all pass | API spec, roadmap milestones, GUI architecture docs updated |

## Metrics

- **PRs:** 2 (#91, #92)
- **E2E tests added:** 8 (6 in effect-workshop.spec.ts, 2 axe-core scans in accessibility.spec.ts)
- **Design documents updated:** 3 (05-api-specification.md, 01-roadmap.md, 08-gui-architecture.md)
- **Roadmap milestones marked complete:** M2.4 (Audio Mixing), M2.5 (Transitions), M2.6 (Effect Registry), M2.8 (GUI Effect Discovery), M2.9 (GUI Effect Builder — 4/5 items)
- **New API endpoints documented:** 3 (POST /effects/preview, PATCH /effects/{index}, DELETE /effects/{index})
- **Total pytest suite:** 864 passed, 20 skipped at theme completion
- **Total vitest suite:** 143 tests (27 test files) at theme completion

## Key Decisions

### Serial mode for stateful E2E tests
**Context:** Apply/edit/remove tests share server-side state (a project with a clip created via API setup). Running them in parallel would cause race conditions.
**Choice:** Used Playwright serial mode for the CRUD test group, with a lazy setup function that generates a minimal test video via ffmpeg, scans it, and creates a project with a clip through the API.
**Outcome:** Reliable test ordering without sacrificing isolation of the stateless tests (catalog browse, parameter config).

### Client-side navigation in E2E tests
**Context:** The SPA fallback for GUI routes is a known limitation (LRN-023). Direct URL navigation to `/gui/effects` would return a 404.
**Choice:** Tests navigate via client-side routing — starting at the root and clicking through the UI to reach effect workshop pages.
**Outcome:** Tests work correctly without requiring server-side SPA fallback configuration, while also exercising the actual user navigation flow.

### Comprehensive doc update as a single feature
**Context:** Three design documents needed updates to reflect v007 changes. Could have been split into separate features per document.
**Choice:** Combined into a single feature (002) with 9 acceptance criteria covering all three documents and the known limitations section.
**Outcome:** Efficient delivery — the documents share cross-references and updating them together ensured consistency.

## Learnings

### What Went Well
- E2E test setup using direct API calls for fixture creation (ffmpeg video generation + scan + project + clip) provides a fast and reliable baseline without depending on the GUI for setup
- axe-core integration for WCAG AA accessibility scanning caught no violations, validating that the component library and workshop UI maintain accessibility standards
- Keyboard navigation test (Tab, Enter, Space through full workflow) provides confidence in accessibility beyond what automated scans detect
- Documentation update was straightforward because the implementation closely followed the original design — minimal divergence to reconcile

### What Could Improve
- E2E tests require ffmpeg/ffprobe in the test environment, which adds a CI dependency. If these binaries are not available, the apply/edit/remove tests will fail during setup
- M2.9 (GUI Effect Builder) has 4/5 sub-items complete — preview thumbnail is not yet implemented, so the milestone is not fully checked off
- No quality-gaps.md files were generated for this theme's features, which may indicate the quality gap analysis step was skipped or there were genuinely no gaps to report

## Technical Debt

### SPA Fallback Still Missing
**Source:** 001 completion-report notes, 002 known limitations section
**Issue:** GUI routes (`/gui/effects`, `/gui/library`, etc.) return 404 when accessed directly. E2E tests work around this via client-side navigation. The API specification now documents this as a known limitation with a workaround.
**Impact:** Users bookmarking or refreshing GUI pages get a 404. E2E tests are constrained to navigate from the root.
**Recommendation:** Implement server-side SPA fallback (catch-all route serving `index.html`) before adding more GUI routes.

### Pre-existing Flaky E2E Test (BL-055, carried from Theme 03)
**Source:** Theme 03 retrospective
**Issue:** `gui/e2e/project-creation.spec.ts:31` — modal hide assertion times out in CI because `POST /api/v1/projects` fails. Unrelated to quality-validation theme.
**Impact:** Continues to block PR merges for GUI-touching features.
**Recommendation:** Remains the highest-priority CI fix needed before the next GUI development cycle.

### Preview Thumbnail Not Implemented (M2.9)
**Source:** 002 completion-report (roadmap update)
**Issue:** M2.9 sub-item 5 (preview thumbnail) is not checked off. The "Visual preview coming in a future version" placeholder exists in the GUI.
**Recommendation:** Track as a future milestone item. Will require a backend render/thumbnail endpoint.

## Recommendations

1. **Fix SPA fallback before next version:** This is now documented in the API specification as a known limitation and affects both E2E test design and real user experience. Should be addressed as infrastructure work.
2. **Resolve BL-055 flaky test:** Two consecutive themes have flagged this as a PR merge blocker. Investigate the CI environment's project-creation endpoint failure.
3. **Ensure ffmpeg availability in CI:** The new E2E tests depend on ffmpeg/ffprobe for test fixture generation. Verify these are available in all CI environments to prevent false failures.
4. **Preview thumbnail as next GUI feature:** The only unchecked M2.9 item is a natural follow-up that would complete the Effect Builder milestone.
