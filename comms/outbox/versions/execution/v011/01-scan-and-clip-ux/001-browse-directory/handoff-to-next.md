# Handoff: 001-browse-directory

## What Was Built

- `GET /api/v1/filesystem/directories?path=...` endpoint for listing subdirectories
- `DirectoryBrowser.tsx` component for visual directory navigation
- Browse button in `ScanModal.tsx` that opens the directory browser

## Key Patterns Used

- **Security**: The endpoint reuses `validate_scan_path()` from `scan.py` to enforce `allowed_scan_roots` restrictions. Path traversal is prevented via `Path.resolve()`.
- **Async I/O**: `os.scandir()` runs in `run_in_executor` to avoid blocking the event loop.
- **Frontend state**: `showBrowser` state in ScanModal controls DirectoryBrowser visibility. The browser passes the selected path back via `onSelect` callback.

## Integration Points

- The filesystem router is registered in `app.py` alongside existing routers
- `DirectoryBrowser` is imported and used only by `ScanModal` — no other components depend on it
- The directory listing API is independent and could be reused by future features that need filesystem browsing

## Notes for Next Feature

- The directory browser uses a flat one-level listing (per LRN-029) — no tree view
- Hidden directories (`.` prefix) are filtered out
- Symlinks are not followed (`follow_symlinks=False` in `os.scandir`)
- No limit on number of entries returned; future features may want to add pagination for very large directories
