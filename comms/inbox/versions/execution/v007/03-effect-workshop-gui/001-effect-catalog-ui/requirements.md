# Requirements: effect-catalog-ui

## Goal

Build grid/list view of available effects with search, filter, and AI hint tooltips.

## Background

Backlog Item: BL-048

M2.8 specifies an effect catalog component for browsing and selecting available effects. The `/effects` discovery endpoint (v006) provides the data, but no UI exists to consume it. This is the entry point for the entire Effect Workshop workflow — users need a visual catalog to discover available effects before configuring and applying them.

## Functional Requirements

**FR-001**: Grid/list view displays available effects fetched from /effects endpoint
- AC: Default view shows effects in a responsive grid layout
- AC: Toggle switches between grid and list views
- AC: Loading state shown while fetching effects
- AC: Error state shown if API call fails with retry option

**FR-002**: Effect cards show name, description, and category
- AC: Each card displays effect name prominently
- AC: Brief description text visible on each card
- AC: Category badge/label shown (e.g., "audio", "video", "transition")

**FR-003**: AI hints displayed as contextual tooltips on each effect
- AC: Hovering over an effect shows AI hint tooltip
- AC: Focus on effect card also shows tooltip (keyboard accessibility)
- AC: Tooltips sourced from ai_hints field in effect definition

**FR-004**: Search and filter by category narrows the displayed effects
- AC: Text search filters effects by name (client-side)
- AC: Category filter dropdown/tabs narrows to selected category
- AC: Combined search + filter works correctly
- AC: Empty results show appropriate message

**FR-005**: Clicking an effect opens its parameter configuration form
- AC: Click/Enter on an effect card sets it as the selected effect
- AC: Selection triggers navigation to or display of parameter form (BL-049)
- AC: Selected state visually indicated on the card

## Non-Functional Requirements

**NFR-001**: Responsive layout works on viewport widths 768px-1920px
- Metric: Grid adjusts column count for different viewport widths

**NFR-002**: Keyboard navigable
- Metric: All interactive elements reachable and operable via Tab/Enter/Space

## Out of Scope

- Effect favoriting or pinning
- Custom effect creation from the UI
- Drag-and-drop effect application

## Test Requirements

- ~3 Vitest tests: EffectCatalog renders cards, grid/list toggle
- ~2 Vitest tests: Search filter narrows by name
- ~2 Vitest tests: Category filter by effect category
- ~1 Vitest test: AI hint tooltip display
- ~1 Vitest test: Click handler triggers selection callback
- ~3 Vitest tests: useEffects hook (fetch, loading, error states)
- ~2 Vitest tests: effectCatalogStore state management

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `codebase-patterns.md`: GUI component patterns, Zustand store pattern, custom hooks