# Implementation Plan: dynamic-parameter-forms

## Overview

Build a custom schema-driven form generator that reads JSON schema from the effect registry and renders appropriate input widgets (number/range, string, enum, boolean, color picker). Adds a form store for parameter state and validation feedback. Integrates with the effect catalog's selected effect.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `gui/src/components/EffectParameterForm.tsx` | Schema-driven form generator component |
| Create | `gui/src/stores/effectFormStore.ts` | Parameter values, validation errors, dirty state |
| Modify | `gui/src/pages/EffectsPage.tsx` | Integrate parameter form with catalog selection |
| Create | `gui/src/components/__tests__/EffectParameterForm.test.tsx` | Component tests |

## Test Files

`gui/src/components/__tests__/EffectParameterForm.test.tsx`

## Implementation Stages

### Stage 1: Form store

1. Create `effectFormStore.ts` following existing store pattern
   - State: parameters (key-value map), validationErrors (per-field), schema, isDirty
   - Actions: setParameter, setSchema, setValidationErrors, resetForm
2. Store initializes from schema defaults when a new effect is selected

**Verification:**
```bash
cd gui && npx vitest run --testPathPattern effectForm
```

### Stage 2: Form generator component

1. Create `EffectParameterForm.tsx` that reads schema from store
2. Render input widgets based on schema property types:
   - `type: "number"` with `minimum`/`maximum` → range slider + numeric input
   - `type: "string"` → text input
   - `type: "string"` with `enum` → dropdown select
   - `type: "boolean"` → checkbox/toggle
   - `format: "color"` → color picker (`<input type="color">`)
3. Pre-populate from schema `default` values
4. Each input has an accessible label from schema property title/key
5. onChange handlers update effectFormStore

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/EffectParameterForm.test.tsx
```

### Stage 3: Validation and integration

1. Add inline validation display (error messages per field)
2. Wire backend validation errors (from API response) to store
3. Integrate form into EffectsPage below catalog
4. Form renders when an effect is selected from catalog

**Verification:**
```bash
cd gui && npx vitest run
```

## Test Infrastructure Updates

- New test file: `EffectParameterForm.test.tsx`
- Mock schemas for each input type

## Quality Gates

```bash
cd gui && npx tsc -b && npx vitest run
```

## Risks

- Schema format must be consistent across all registered effects. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(gui): add schema-driven parameter form generator for effects
```