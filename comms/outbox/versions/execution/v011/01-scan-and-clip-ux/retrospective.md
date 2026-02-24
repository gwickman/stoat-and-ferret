# Theme Retrospective: 01-scan-and-clip-ux

## Theme Summary

This theme delivered the missing GUI interaction layer for media scanning and clip management in stoat-and-ferret. Two features closed longstanding gaps: a directory browser for scan path selection (BL-070) and full clip CRUD controls wired to existing backend endpoints (BL-075). Both features shipped with all acceptance criteria passing and clean quality gates.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Status | PR |
|---|---------|------------|---------------|--------|----|
| 001 | browse-directory | 8/8 PASS | ruff, mypy, pytest, vitest all pass | Complete | #108 |
| 002 | clip-crud-controls | 9/9 PASS | ruff, mypy, pytest, tsc, vitest all pass | Complete | #109 |

**Overall:** 2/2 features complete, 17/17 acceptance criteria passing.

## Key Learnings

### What Went Well

- **Reusing existing infrastructure** — The browse-directory feature reused `validate_scan_path()` from the scan module for security validation, avoiding duplicate path-safety logic. The clip-crud feature wired to already-existing backend endpoints (POST/PATCH/DELETE) rather than creating new ones.
- **Established frontend patterns scaled** — The clip store followed the `effectStackStore` Zustand pattern, and the ClipFormModal followed existing modal patterns (ScanModal). Consistency made implementation straightforward.
- **Async I/O handled correctly** — The filesystem endpoint used `run_in_executor` for `os.scandir()` to avoid blocking the event loop, following the project's async-first approach.
- **Clean quality gates on first pass** — Both features passed ruff, mypy, pytest, and frontend tests without iteration cycles.

### Patterns Discovered

- **Flat directory listing over tree view** — Per LRN-029, a flat one-level directory listing was chosen over a tree view. This kept the component simple and avoids loading deep directory structures upfront.
- **Overlay pattern for sub-components** — DirectoryBrowser renders as an overlay within ScanModal rather than a separate route or dialog, keeping the user in context.
- **Zustand store per entity** — clipStore follows the per-entity store pattern (like effectStackStore), keeping state management granular and testable.

## Technical Debt

| Item | Source | Severity | Notes |
|------|--------|----------|-------|
| No pagination on directory listing | 001-browse-directory handoff | Low | Large directories could return many entries; not a problem for typical use but may need pagination for edge cases |
| Hidden directory filtering is frontend-convention only | 001-browse-directory handoff | Low | Dot-prefix filtering happens in the backend endpoint; if other consumers need hidden dirs, an option would be needed |
| Symlinks not followed in directory browser | 001-browse-directory handoff | Low | `follow_symlinks=False` in `os.scandir` — correct default but may surprise users with symlinked media dirs |

## Recommendations

1. **For future GUI features** — Continue following the pattern of wiring frontend to existing backend endpoints before creating new ones. Both features in this theme succeeded because the backend surface was already mature.
2. **Directory browser reuse** — The `DirectoryBrowser` component and `/api/v1/filesystem/directories` endpoint are decoupled from scan-specific logic and could be reused by any future feature needing filesystem browsing (e.g., export path selection).
3. **Store testing pattern** — The clipStore test approach (mocking fetch, testing CRUD + error states) is a good template for future Zustand store tests.
