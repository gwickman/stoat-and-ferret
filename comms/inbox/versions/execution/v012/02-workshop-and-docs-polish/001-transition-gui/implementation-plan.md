# Implementation Plan: transition-gui

## Overview

Wire transition effects into the Effect Workshop GUI by creating a useTransitionStore Zustand store, extending ClipSelector with pair-mode props, creating a TransitionPanel component, and adding a Transitions tab to the EffectsPage. The backend endpoint already exists — this is entirely frontend work following established Effect Workshop patterns.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/src/stores/transitionStore.ts` | Create | Zustand store for source/target clip selection and transition state |
| `gui/src/components/ClipSelector.tsx` | Modify | Add optional pair-mode props (pairMode, selectedFromId, selectedToId, onSelectPair) |
| `gui/src/components/TransitionPanel.tsx` | Create | Main transition UI integrating clip-pair selection, type catalog, parameter form, submit |
| `gui/src/pages/EffectsPage.tsx` | Modify | Add Transitions tab alongside existing per-clip effects |
| `gui/src/stores/__tests__/transitionStore.test.ts` | Create | Tests for transition store |
| `gui/src/components/__tests__/ClipSelector.test.tsx` | Modify | Add pair-mode selection tests |
| `gui/src/components/__tests__/TransitionPanel.test.tsx` | Create | Tests for TransitionPanel component |

## Test Files

`gui/src/stores/__tests__/transitionStore.test.ts gui/src/components/__tests__/ClipSelector.test.tsx gui/src/components/__tests__/TransitionPanel.test.tsx`

Post-implementation: `cd gui && npx vitest run`

## Implementation Stages

### Stage 1: Create useTransitionStore

1. Read existing store patterns: `gui/src/stores/effectStackStore.ts`, `gui/src/stores/effectFormStore.ts`
2. Create `gui/src/stores/transitionStore.ts` with:
   - `sourceClipId: string | null`
   - `targetClipId: string | null`
   - `selectSource(clipId)` — sets source, clears target
   - `selectTarget(clipId)` — sets target
   - `isReady()` — both source and target selected
   - `reset()` — clears both
3. Create `gui/src/stores/__tests__/transitionStore.test.ts`

**Verification**: `cd gui && npx vitest run src/stores/__tests__/transitionStore.test.ts`

### Stage 2: Extend ClipSelector with pair-mode

1. Read `gui/src/components/ClipSelector.tsx` (~50 lines)
2. Add optional props: `pairMode?: boolean`, `selectedFromId?: string | null`, `selectedToId?: string | null`, `onSelectPair?: (clipId: string, role: 'from' | 'to') => void`
3. When `pairMode` is true, render clips with "from"/"to" visual differentiation via color coding
4. Existing single-select API remains unchanged — pair-mode is opt-in
5. Update `gui/src/components/__tests__/ClipSelector.test.tsx` with pair-mode tests

**Verification**: `cd gui && npx vitest run src/components/__tests__/ClipSelector.test.tsx`

### Stage 3: Create TransitionPanel

1. Read `gui/src/pages/EffectsPage.tsx` for integration patterns
2. Read `gui/src/components/EffectCatalog.tsx` and `gui/src/components/EffectParameterForm.tsx` for schema-driven patterns
3. Read `gui/src/hooks/useEffects.ts` for transition category derivation (lines 31-43)
4. Create `gui/src/components/TransitionPanel.tsx`:
   - ClipSelector in pair-mode for source/target selection
   - Transition type catalog (filtered to "transition" category: xfade, acrossfade)
   - Schema-driven parameter form using EffectParameterForm
   - Submit button calling `POST /projects/{id}/effects/transition`
   - Error handling for NOT_ADJACENT (400) response
5. Create `gui/src/components/__tests__/TransitionPanel.test.tsx`

**Verification**: `cd gui && npx vitest run src/components/__tests__/TransitionPanel.test.tsx`

### Stage 4: Integrate into EffectsPage

1. Read `gui/src/pages/EffectsPage.tsx` (263 lines)
2. Add tab/mode toggle between "Effects" (existing) and "Transitions" (new)
3. When "Transitions" mode is active, render TransitionPanel instead of per-clip effect UI
4. Ensure existing per-clip effect flow remains unchanged

**Verification**: `cd gui && npx tsc -b && npx vitest run`

## Test Infrastructure Updates

- Create `gui/src/stores/__tests__/transitionStore.test.ts`
- Update `gui/src/components/__tests__/ClipSelector.test.tsx` (add pair-mode tests)
- Create `gui/src/components/__tests__/TransitionPanel.test.tsx`

## Quality Gates

```bash
cd gui
npx tsc -b
npx vitest run
```

## Risks

- ClipSelector pair-mode extension adds ~30-40 lines; preserves existing API via optional props
- Backend adjacency validation handles correctness — GUI provides UX convenience only
- See `comms/outbox/versions/design/v012/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(v012): add transition support to Effect Workshop GUI

Wire transition effects into the Effect Workshop with
useTransitionStore, ClipSelector pair-mode, and TransitionPanel.
Users can select adjacent clips, choose transition types, and
apply via the existing backend endpoint.

Closes BL-066
```