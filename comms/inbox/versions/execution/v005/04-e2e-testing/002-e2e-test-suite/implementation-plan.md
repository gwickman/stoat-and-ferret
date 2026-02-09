# Implementation Plan - 002: E2E Test Suite

## Overview

Write E2E tests covering the three key user flows (navigation, scan trigger, project creation) plus WCAG AA accessibility checks on each main view using `@axe-core/playwright`.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/e2e/navigation.spec.ts` | Create | Tab navigation E2E test |
| `gui/e2e/scan.spec.ts` | Create | Library scan trigger E2E test |
| `gui/e2e/project-creation.spec.ts` | Create | Project creation flow E2E test |
| `gui/e2e/accessibility.spec.ts` | Create | WCAG AA accessibility checks |
| `gui/e2e/example.spec.ts` | Modify | Remove or keep as baseline smoke test |

## Implementation Stages

### Stage 1: Navigation Test

1. Create `navigation.spec.ts`:
   - Navigate to `/gui/` (dashboard loads by default)
   - Click Library tab, verify URL changes to `/gui/library` and library content renders
   - Click Projects tab, verify URL changes to `/gui/projects` and projects content renders
   - Click Dashboard tab, verify return to dashboard
2. Assert each page renders its primary heading/content

**Verification:**
```bash
cd gui && npx playwright test navigation.spec.ts
```

### Stage 2: Scan Trigger Test

1. Create `scan.spec.ts`:
   - Navigate to `/gui/library`
   - Click scan button to open scan modal
   - Enter a directory path in the modal input
   - Submit the scan
   - Verify scan feedback appears (progress indicator or status message)
2. May need to mock or use a test directory for scan target

**Verification:**
```bash
cd gui && npx playwright test scan.spec.ts
```

### Stage 3: Project Creation Test

1. Create `project-creation.spec.ts`:
   - Navigate to `/gui/projects`
   - Click "New Project" button to open creation modal
   - Fill in project name, resolution, fps, format
   - Submit the form
   - Verify new project appears in the project list
2. Verify form validation by testing invalid inputs

**Verification:**
```bash
cd gui && npx playwright test project-creation.spec.ts
```

### Stage 4: Accessibility Checks

1. Create `accessibility.spec.ts`:
   - Navigate to dashboard, run `@axe-core/playwright` with `withTags(['wcag2a', 'wcag2aa'])`
   - Navigate to library, run accessibility check
   - Navigate to projects, run accessibility check
2. Assert `results.violations` is empty for each view

**Verification:**
```bash
cd gui && npx playwright test accessibility.spec.ts
cd gui && npx playwright test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- E2E tests in `gui/e2e/` directory alongside Playwright config
- Tests run against FastAPI serving built frontend via webServer config
- Accessibility tests use `@axe-core/playwright` for WCAG AA validation

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
cd gui && npx playwright test
```

## Risks

- **Test stability:** E2E tests may be flaky due to timing. Use Playwright auto-waiting and avoid hard `sleep()` calls. CI retries (max 2) provide resilience.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: add E2E tests for navigation, scan, project creation, and accessibility

- Add navigation test verifying tab switching and URL routing
- Add scan trigger test from library browser
- Add project creation flow test (modal, form, submit, verify)
- Add WCAG AA accessibility checks on all main views

Implements BL-036 (test suite portion)
```