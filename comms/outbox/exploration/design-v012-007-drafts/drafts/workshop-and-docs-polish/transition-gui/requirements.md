# Feature: transition-gui

## Goal

Wire transition effects into the Effect Workshop GUI via the existing backend endpoint, enabling users to discover and apply transitions between adjacent clips.

## Background

The `POST /projects/{id}/effects/transition` endpoint was implemented in v007/02-effect-registry-api and is fully functional with adjacency validation. However, the Effect Workshop GUI (v007/03) was scoped to per-clip effects only. There is no GUI surface for the transition API — transitions are only accessible via direct API calls.

Backlog Item: BL-066

## Functional Requirements

**FR-001**: Create `useTransitionStore` Zustand store
- Acceptance: Store manages source/target clip selection, reset, and isReady computed state following the slices pattern

**FR-002**: Extend `ClipSelector` component with optional pair-mode props
- Acceptance: ClipSelector supports optional `pairMode`, `selectedFromId`, `selectedToId`, `onSelectPair` props while preserving existing single-select API unchanged

**FR-003**: Create `TransitionPanel` component
- Acceptance: Component integrates clip-pair selection (via extended ClipSelector), transition type catalog, parameter form, and submit flow

**FR-004**: Add Transitions tab to Effect Workshop
- Acceptance: `gui/src/pages/EffectsPage.tsx` includes a "Transitions" tab or mode distinct from per-clip effects

**FR-005**: Display available transition types from effect catalog
- Acceptance: GUI shows xfade and acrossfade transition types from the existing catalog

**FR-006**: Render schema-driven parameter forms for transitions
- Acceptance: Parameter forms follow the existing schema-driven pattern (JSON Schema to form fields)

**FR-007**: Submit transition via backend endpoint
- Acceptance: Submitting calls `POST /projects/{id}/effects/transition` with source_clip_id, target_clip_id, transition_type, and parameters; transition is stored on the project

**FR-008**: Handle non-adjacent clip error feedback
- Acceptance: User receives appropriate error message when backend returns 400 NOT_ADJACENT

## Non-Functional Requirements

**NFR-001**: No TypeScript errors
- Metric: `npx tsc -b` passes in `gui/`

**NFR-002**: All frontend tests pass
- Metric: `npx vitest run` exits 0 in `gui/`

**NFR-003**: Consistent UX patterns
- Metric: TransitionPanel follows existing Effect Workshop visual patterns (catalog, parameter forms, preview)

## Handler Pattern

Not applicable for v012 — no new handlers introduced.

## Out of Scope

- Backend endpoint modifications (already functional)
- Transition preview/rendering (future enhancement)
- Drag-and-drop transition placement on a visual timeline
- C4 documentation updates (tracked as BL-069)

## Test Requirements

- `gui/src/stores/__tests__/transitionStore.test.ts` — source/target selection, reset, isReady state
- `gui/src/components/__tests__/ClipSelector.test.tsx` — update existing tests, add pair-mode selection tests
- `gui/src/components/__tests__/TransitionPanel.test.tsx` — transition type selection, parameter form rendering, submit flow
- Post-implementation: `npx vitest run`, `npx tsc -b`

## Reference

See `comms/outbox/versions/design/v012/004-research/` for supporting evidence.
