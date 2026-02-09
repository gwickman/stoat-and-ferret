# Implementation Plan - 004: Project Manager

## Overview

Build the project manager with a project list, creation modal with form validation, details view showing clips with Rust-calculated timeline positions, and delete confirmation dialog. Consumes the projects API established in v003.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/src/pages/ProjectsPage.tsx` | Modify | Replace placeholder with full project manager |
| `gui/src/components/ProjectList.tsx` | Create | Project list with name, date, clip count |
| `gui/src/components/ProjectCard.tsx` | Create | Individual project card |
| `gui/src/components/CreateProjectModal.tsx` | Create | Project creation form with validation |
| `gui/src/components/ProjectDetails.tsx` | Create | Project details with clip timeline |
| `gui/src/components/DeleteConfirmation.tsx` | Create | Delete confirmation dialog |
| `gui/src/hooks/useProjects.ts` | Create | Projects API hook |
| `gui/src/stores/projectStore.ts` | Create | Zustand store for project state |
| `gui/src/components/__tests__/ProjectList.test.tsx` | Create | Project list tests |
| `gui/src/components/__tests__/CreateProjectModal.test.tsx` | Create | Creation modal tests |
| `gui/src/components/__tests__/ProjectDetails.test.tsx` | Create | Project details tests |
| `gui/src/components/__tests__/DeleteConfirmation.test.tsx` | Create | Delete confirmation tests |

## Implementation Stages

### Stage 1: Project List

1. Create `useProjects` hook: fetch from `/api/v1/projects` with list/get/create/delete operations
2. Create `projectStore` with Zustand for project list, selected project, and modal state
3. Create `ProjectCard.tsx`: display project name, formatted creation date, and clip count
4. Create `ProjectList.tsx`: render `ProjectCard` components in a list layout

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 2: Creation Modal

1. Create `CreateProjectModal.tsx` with form fields for project name, resolution (e.g., 1920x1080), fps (e.g., 24, 30, 60), and format
2. Implement client-side validation: required fields, valid resolution format, fps range
3. Submit validated form to `POST /api/v1/projects`
4. Close modal and refresh project list on success

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 3: Details View and Delete

1. Create `ProjectDetails.tsx`: display project metadata and clip list with Rust-calculated timeline positions (start/end times from API)
2. Create `DeleteConfirmation.tsx`: modal dialog with project name confirmation
3. Wire delete button to show confirmation; confirmed delete calls `DELETE /api/v1/projects/{id}`
4. Refresh project list after successful delete
5. Assemble all components in `ProjectsPage.tsx`

**Verification:**
```bash
cd gui && npx vitest run
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Vitest tests with mocked fetch for projects API
- Vitest tests for form validation logic
- Vitest tests for delete confirmation flow

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

None specific to this feature. Project manager consumes established API from v003.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: build project manager with list, creation, and details views

- Create project list displaying name, date, and clip count
- Add creation modal with resolution/fps/format validation
- Implement details view with Rust-calculated timeline positions
- Add delete confirmation dialog with project name verification

Implements BL-035
```