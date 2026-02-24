# Implementation Plan: browse-directory

## Overview

Add a backend directory listing endpoint (`GET /api/v1/filesystem/directories`) that reuses existing `validate_scan_path()` security, and a frontend `DirectoryBrowser.tsx` component with a Browse button in `ScanModal.tsx`. The endpoint uses `run_in_executor` for async-safe `os.scandir()` calls.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/stoat_ferret/api/routers/filesystem.py` | Create | New router with `GET /api/v1/filesystem/directories` endpoint |
| `src/stoat_ferret/api/schemas/filesystem.py` | Create | Pydantic request/response models for directory listing |
| `src/stoat_ferret/api/app.py` | Modify | Register new filesystem router |
| `gui/src/components/DirectoryBrowser.tsx` | Create | Directory browser component (flat list, one level) |
| `gui/src/components/ScanModal.tsx` | Modify | Add Browse button that opens DirectoryBrowser |
| `tests/test_api/test_filesystem.py` | Create | Backend tests for directory listing endpoint |
| `gui/src/components/__tests__/DirectoryBrowser.test.tsx` | Create | Frontend tests for DirectoryBrowser component |
| `gui/src/components/__tests__/ScanModal.test.tsx` | Modify | Update for browse button interaction |
| `docs/design/05-api-specification.md` | Modify | Add directory listing endpoint documentation |

## Test Files

`tests/test_api/test_filesystem.py gui/src/components/__tests__/DirectoryBrowser.test.tsx gui/src/components/__tests__/ScanModal.test.tsx`

## Implementation Stages

### Stage 1: Backend endpoint

1. Create `src/stoat_ferret/api/schemas/filesystem.py` with `DirectoryListResponse` model (list of directory entries with name and full path)
2. Create `src/stoat_ferret/api/routers/filesystem.py`:
   - `GET /api/v1/filesystem/directories` with `path` query parameter
   - Import `validate_scan_path()` from `src/stoat_ferret/api/services/scan.py`
   - Call `validate_scan_path()` on the requested path
   - Use `await asyncio.get_event_loop().run_in_executor(None, _list_dirs, path)` for `os.scandir()`
   - Filter to directories only (skip files, skip entries starting with `.`)
   - Return sorted directory names and full paths
   - Handle errors: 400 (not a directory), 403 (outside allowed roots), 404 (path doesn't exist)
   - When `allowed_scan_roots` is non-empty, default browse path is first root; when empty, use platform-appropriate default
3. Register router in `src/stoat_ferret/api/app.py`
4. Write `tests/test_api/test_filesystem.py`:
   - Test valid directory listing
   - Test non-existent path returns 404
   - Test file path returns 400
   - Test path outside allowed roots returns 403
   - Test path traversal (`../`) rejected

**Verification:**
```bash
uv run pytest tests/test_api/test_filesystem.py -v
uv run ruff check src/stoat_ferret/api/routers/filesystem.py src/stoat_ferret/api/schemas/filesystem.py
uv run mypy src/stoat_ferret/api/routers/filesystem.py src/stoat_ferret/api/schemas/filesystem.py
```

### Stage 2: Frontend components

1. Create `gui/src/components/DirectoryBrowser.tsx`:
   - Props: `onSelect(path: string)`, `onCancel()`, `initialPath?: string`
   - State: `currentPath`, `directories`, `isLoading`, `error`
   - Fetch `GET /api/v1/filesystem/directories?path={currentPath}` on mount and path change
   - Render: breadcrumb/path display, directory list, select/navigate buttons, cancel button
   - Clicking a directory navigates into it; a "Select" button confirms the current path
   - Style with existing Tailwind patterns (modal overlay, list items)
2. Modify `gui/src/components/ScanModal.tsx`:
   - Add `showBrowser` state
   - Add Browse button next to path input
   - When Browse clicked, show `DirectoryBrowser` overlay
   - On directory selected, set path input value and close browser
3. Write `gui/src/components/__tests__/DirectoryBrowser.test.tsx`:
   - Renders loading state
   - Renders directory list
   - Renders empty state
   - Selecting directory calls onSelect with correct path
   - Navigating into subdirectory triggers new fetch
4. Update `gui/src/components/__tests__/ScanModal.test.tsx`:
   - Browse button renders
   - Browse button opens DirectoryBrowser

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/DirectoryBrowser.test.tsx src/components/__tests__/ScanModal.test.tsx
```

### Stage 3: Documentation and integration

1. Update `docs/design/05-api-specification.md` with new endpoint documentation

**Verification:**
```bash
uv run pytest tests/test_api/test_filesystem.py -v
cd gui && npx vitest run
```

## Test Infrastructure Updates

New test files:
- `tests/test_api/test_filesystem.py` — backend endpoint tests (5 cases)
- `gui/src/components/__tests__/DirectoryBrowser.test.tsx` — component tests (5 cases)

Existing test updates:
- `gui/src/components/__tests__/ScanModal.test.tsx` — add browse button interaction tests

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ -v
cd gui && npx vitest run
```

## Risks

- Filesystem permission errors on certain directories — handle gracefully with error response
- Large directory listings — `os.scandir()` is efficient but consider adding a limit parameter in future
- See `comms/outbox/versions/design/v011/006-critical-thinking/risk-assessment.md` for full risk analysis

## Commit Message

```
feat(gui): add directory browser for scan path selection (BL-070)
```
