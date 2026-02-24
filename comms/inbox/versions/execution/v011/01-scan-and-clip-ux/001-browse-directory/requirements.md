# Requirements: browse-directory

## Goal

Replace the text-only scan path input with a backend-assisted directory browser so users can visually navigate to and select scan directories.

## Background

Backlog Item: BL-070 — Add Browse button for scan directory path selection.

Currently the Scan Directory feature in ScanModal requires users to manually type or paste a directory path. There is no folder browser dialog. This creates friction — users must know the exact path. The `showDirectoryPicker()` API is not viable (Firefox/Safari lack support), so a backend-assisted directory listing endpoint is needed.

## Functional Requirements

**FR-001: Directory listing endpoint**
- The backend provides `GET /api/v1/filesystem/directories?path={parent_path}` returning subdirectories within the given path
- Acceptance: Endpoint returns a JSON list of subdirectory names/paths for a valid directory path

**FR-002: Security validation**
- The endpoint imports and calls `validate_scan_path()` from `src/stoat_ferret/api/services/scan.py` to enforce `allowed_scan_roots` restrictions
- Path normalization uses `Path.resolve()` (matching existing codebase convention)
- Acceptance: Paths outside `allowed_scan_roots` return 403; path traversal attempts (`../`) are rejected

**FR-003: Async filesystem access**
- The endpoint uses `run_in_executor` for `os.scandir()` calls to avoid blocking the event loop
- Acceptance: Directory listing completes without blocking concurrent requests

**FR-004: Browse button in ScanModal**
- ScanModal includes a Browse button next to the path input field
- Clicking Browse opens a `DirectoryBrowser` component
- Acceptance: Browse button renders and opens the directory browser on click

**FR-005: Directory browser component**
- `DirectoryBrowser.tsx` renders a flat list of subdirectories (one level at a time)
- Selecting a directory either navigates into it (showing its children) or confirms it as the chosen path
- Acceptance: Users can navigate directory hierarchy and select a target directory

**FR-006: Path population**
- Selecting a directory in the browser populates the ScanModal path input with the chosen path
- Acceptance: After selection, the path input contains the full path of the selected directory

**FR-007: Manual path fallback**
- Users can still manually type a path in the input field as an alternative to browsing
- Acceptance: Typed paths continue to work as before the browse feature was added

**FR-008: Initial browse path**
- When `allowed_scan_roots` is non-empty, start at the first root
- When empty (all paths allowed), start at a platform-appropriate default (e.g., user home)
- Acceptance: Browse opens to a sensible starting location

## Non-Functional Requirements

**NFR-001: Response time**
- Directory listing responds within 500ms for directories with up to 1000 entries
- Metric: p95 response time < 500ms under normal filesystem conditions

**NFR-002: Error handling**
- Non-existent paths return 404, non-directory paths return 400, restricted paths return 403
- Backend errors are displayed clearly in the browse UI

## Handler Pattern

**New Handler:** `GET /api/v1/filesystem/directories`
- Pattern: async handler with `run_in_executor` for `os.scandir()`
- Rationale: Filesystem I/O can block for large directories (~5-50ms typical, longer for network mounts). `run_in_executor` matches the v010 async pattern used for ffprobe. Security validation (`validate_scan_path()`) is CPU-only and runs synchronously.

## Out of Scope

- Tree view or multi-level directory display (flat one-level listing per LRN-029)
- `showDirectoryPicker()` integration (deferred until Firefox/Safari support)
- File listing within directories (only directories shown)
- Creating or modifying directories from the browser

## Test Requirements

**Backend (pytest):**
- Directory listing endpoint: valid path returns subdirectory list
- Directory listing endpoint: invalid/non-existent path returns 404/400
- Directory listing endpoint: path outside `allowed_scan_roots` returns 403
- Directory listing endpoint: path pointing to a file (not directory) returns 400
- Security: path traversal attempts (e.g., `../`) are rejected

**Frontend (Vitest):**
- `DirectoryBrowser.tsx`: renders loading state, directory list, empty state
- `DirectoryBrowser.tsx`: selecting a directory calls the onSelect callback with correct path
- `DirectoryBrowser.tsx`: navigating into a subdirectory triggers new API fetch
- `ScanModal.tsx`: browse button renders and opens DirectoryBrowser
- `ScanModal.tsx`: selecting a directory in browser populates the path input

**Parity:**
- New `GET /api/v1/filesystem/directories` endpoint: request/response schema validation

## Reference

See `comms/outbox/versions/design/v011/004-research/` for supporting evidence:
- `external-research.md` — browser API evaluation, backend-assisted approach rationale
- `codebase-patterns.md` — scan endpoint patterns, `allowed_scan_roots` security
- `evidence-log.md` — `showDirectoryPicker` browser support data