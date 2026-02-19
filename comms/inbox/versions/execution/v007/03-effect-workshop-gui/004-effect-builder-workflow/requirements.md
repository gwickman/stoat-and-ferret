# Requirements: effect-builder-workflow

## Goal

Compose catalog, form, and preview into full workflow with clip selector, effect stack visualization, and effect CRUD (edit/remove).

## Background

Backlog Item: BL-051

M2.9 specifies a complete effect builder workflow: select effect, configure parameters, choose target clip, view the effect stack per clip, and edit/remove applied effects. Individual components (catalog, form, preview) from T03-F001/F002/F003 need to be composed into a coherent workflow. This feature also adds the backend CRUD endpoints (PATCH/DELETE) for editing and removing effects.

Design clarification: BL-051 AC #3 ("Preview thumbnail") is implemented as a filter string preview panel showing the generated FFmpeg command, not a rendered thumbnail. This satisfies the transparency intent. Rendered thumbnails documented as future enhancement.

## Functional Requirements

**FR-001**: Apply to Clip workflow presents a clip selector from the current project
- AC: ClipSelector component shows all clips in the current project
- AC: Each clip displays its name/filename and position in timeline
- AC: Selecting a clip sets it as the target for effect application
- AC: No clip selected state handled gracefully

**FR-002**: Effect stack visualization shows all effects applied to a selected clip in order
- AC: EffectStack component renders ordered list of effects for the selected clip
- AC: Each effect entry shows effect type, key parameters, and applied filter string
- AC: Empty effect stack shows appropriate message
- AC: Effect ordering reflects application order

**FR-003**: Preview shows filter string for the effect being configured
- AC: Filter string preview panel (from T03-F003) integrated into the workflow
- AC: Shows live preview as parameters change during configuration
- AC: Placeholder text notes "visual preview coming in a future version"

**FR-004**: Edit action re-opens parameter form with existing values for an applied effect
- AC: PATCH /projects/{id}/clips/{id}/effects/{index} endpoint updates effect at array index
- AC: Click "Edit" on an effect opens parameter form pre-filled with current values
- AC: Saving updates the effect in-place at the same array index
- AC: Invalid index returns 404

**FR-005**: Remove action deletes an effect from a clip's effect stack with confirmation
- AC: DELETE /projects/{id}/clips/{id}/effects/{index} endpoint removes effect at array index
- AC: Click "Remove" shows confirmation dialog
- AC: Confirming deletion removes the effect and updates the stack display
- AC: Invalid index returns 404

## Non-Functional Requirements

**NFR-001**: Full workflow completes in under 3 user interactions (select effect, configure, apply)
- Metric: Apply to Clip requires click effect, fill form, click apply

**NFR-002**: CRUD endpoint responses match OpenAPI specification
- Metric: Contract tests validate response schemas

## Out of Scope

- Effect reordering via drag-and-drop
- Multi-effect batch operations
- Undo/redo for effect changes
- Effect templates or presets

## Test Requirements

Frontend (Vitest):
- ~3 tests: ClipSelector renders clips, selection handler
- ~2 tests: EffectStack renders ordered effects
- ~1 test: Edit action opens form with existing values
- ~2 tests: Remove action shows confirmation, calls delete
- ~3 tests: effectStackStore per-clip operations
- ~1 integration test: EffectsPage composes all components

Backend (Python):
- ~3 tests: PATCH /projects/{id}/clips/{id}/effects/{index}
- ~3 tests: DELETE /projects/{id}/clips/{id}/effects/{index}
- ~2 tests: Invalid index handling (out-of-range returns 404)
- ~1 golden test: Full workflow (select, configure, apply, verify stack)
- ~2 parity tests: CRUD responses match OpenAPI spec
- ~2 contract tests: EffectUpdateRequest/EffectDeleteResponse schemas

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `codebase-patterns.md`: Effects storage format, CRUD approach
- `evidence-log.md`: Array-index-based CRUD rationale