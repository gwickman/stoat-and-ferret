# Requirements - 004: Project Manager

## Goal

Build the project manager with project list, creation modal, details view with Rust-calculated timeline positions, and delete confirmation dialog.

## Background

M1.12 specifies a project manager with project list, creation modal, and details view showing Rust-calculated timeline positions. No frontend components for project management exist. The project API endpoints exist from v003 but have no GUI consumer. This is the last GUI milestone in Phase 1.

**Backlog Item:** BL-035

## Functional Requirements

**FR-001: Project list**
Display project list with name, creation date, and clip count for each project.
- AC: Project list shows name, formatted creation date, and clip count per project

**FR-002: Creation modal**
New Project modal with form validation for output settings (resolution, fps, format).
- AC: Creation modal validates resolution, fps, and format inputs; invalid inputs show error messages

**FR-003: Project creation**
Submit validated form to create a new project via the projects API. New project appears in list after creation.
- AC: Submitting the creation form creates a project and updates the project list

**FR-004: Details view**
Project details view displays clip list with Rust-calculated timeline positions (start/end times).
- AC: Details view shows each clip's timeline position as calculated by the Rust core

**FR-005: Delete confirmation**
Delete action requires a confirmation dialog before execution. Confirmed delete calls the projects API.
- AC: Delete button shows confirmation dialog; confirming deletes the project; canceling preserves it

## Non-Functional Requirements

**NFR-001: Form validation responsiveness**
Form validation feedback appears within 100ms of input change.
- Metric: Validation error/success indicators update within 100ms

## Out of Scope

- Project export or rendering
- Timeline editing or clip reordering
- Project sharing or collaboration
- Undo/redo for project modifications

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests (Vitest) | Project list renders name, date, clip count; creation modal validates resolution/fps/format inputs; details view displays clip list with timeline positions; delete button shows confirmation dialog; confirmed delete calls API |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.