# Implementation Plan: e2e-effect-workshop-tests

## Overview

Create Playwright E2E tests covering the full effect workshop workflow: browse catalog, configure parameters, verify preview, apply/edit/remove effects. Include axe-core WCAG AA accessibility scans for all form components. Tests navigate via client-side routing (SPA fallback still deferred, LRN-023).

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `gui/e2e/effect-workshop.spec.ts` | E2E tests for effect workshop workflow |
| Modify | `gui/e2e/accessibility.spec.ts` | Add accessibility tests for effect workshop forms |

## Test Files

`gui/e2e/effect-workshop.spec.ts gui/e2e/accessibility.spec.ts`

## Implementation Stages

### Stage 1: Setup and catalog test

1. Create `effect-workshop.spec.ts`
2. Test: Navigate to effect workshop via navigation click (not direct URL)
3. Test: Effect catalog loads, displays effects
4. Test: Click on an effect to select it

**Verification:**
```bash
cd gui && npx playwright test effect-workshop.spec.ts --grep "catalog"
```

### Stage 2: Parameter configuration and preview test

1. Test: Parameter form renders for selected effect
2. Test: Change a parameter value
3. Test: Filter string preview updates after debounce

**Verification:**
```bash
cd gui && npx playwright test effect-workshop.spec.ts --grep "parameter"
```

### Stage 3: Apply, edit, remove tests

1. Test: Select target clip, apply effect, verify in effect stack
2. Test: Edit applied effect — form opens with existing values, update and save
3. Test: Remove applied effect — confirmation dialog, confirm, verify removal

**Verification:**
```bash
cd gui && npx playwright test effect-workshop.spec.ts --grep "apply|edit|remove"
```

### Stage 4: Accessibility tests

1. Add WCAG AA axe-core scan for effect catalog page
2. Add axe-core scan for parameter form components
3. Verify: all inputs have labels, color contrast AA, keyboard navigation
4. Add to `accessibility.spec.ts` or integrate within workshop tests

**Verification:**
```bash
cd gui && npx playwright test effect-workshop.spec.ts accessibility.spec.ts
```

## Test Infrastructure Updates

- New E2E test file: `effect-workshop.spec.ts`
- May need test data setup (project with clips) in beforeEach
- Uses existing Playwright + axe-core infrastructure from v005

## Quality Gates

```bash
cd gui && npx tsc -b && npx vitest run && npx playwright test
```

## Risks

- SPA fallback missing — tests must navigate via client-side routing. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- E2E tests depend on all prior features being complete and working

## Commit Message

```
test(e2e): add effect workshop E2E tests with accessibility checks
```